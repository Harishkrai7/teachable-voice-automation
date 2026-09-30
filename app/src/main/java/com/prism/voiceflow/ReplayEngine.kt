package com.prism.voiceflow

import android.content.Intent
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import kotlinx.coroutines.delay

/**
 * Executes a replay plan step by step:
 * inspect UI -> safety check -> resolve target -> act -> wait for UI to settle.
 * When a target can't be found it asks Cloud for a constrained recovery decision,
 * re-validates any proposed target itself, and never taps blindly or loops.
 */
class ReplayEngine(private val svc: VoiceFlowService, private val cloud: CloudClient) {

    private val ex get() = svc.executor
    private val root: AccessibilityNodeInfo? get() = svc.rootInActiveWindow

    private fun status(msg: String) {
        Log.i(TAG, msg)
        svc.overlay.show(msg, "Stop") { svc.cancelReplay() }
    }

    suspend fun run(plan: ReplayResponse): String {
        val app = plan.app ?: return "⚠️ Plan has no app."
        val launch = svc.packageManager.getLaunchIntentForPackage(app)
            ?: return "⚠️ $app is not installed."
        status("Opening app…")
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        svc.startActivity(launch)
        if (!waitFor(12_000) { root?.packageName?.toString() == app }) return "⚠️ Couldn't open $app."
        settle(minMs = 2000, maxMs = 5000)

        val total = plan.steps.size
        var prevWasType = false
        for (step in plan.steps) {
            for (r in 0 until maxOf(1, step.repeat)) {
                val rep = if (step.repeat > 1) " (${r + 1}/${step.repeat})" else ""
                status("Step ${step.index + 1}/$total: ${describe(step)}$rep")
                doStep(plan.flowId ?: "", step, prevWasType && r == 0)?.let { return it }
            }
            prevWasType = step.type == "TYPE"
        }
        return "✅ Done: all $total steps. I stopped before payment — your turn to review and pay."
    }

    /** Returns null on success, or a user-facing message describing where/why it stopped. */
    private suspend fun doStep(flowId: String, step: Step, afterType: Boolean): String? {
        SafetyGate.sensitiveScreen(root)?.let { return stop("Your turn — this screen needs you ($it).") }

        when (step.type) {
            "BACK" -> { ex.back(); settle(); return null }
            "ENTER" -> { ex.enter(root); settle(); return null }
            "SCROLL" -> { ex.scrollForward(root); settle(); return null }
        }
        val t = step.target ?: return "⚠️ Step ${step.index + 1} has no target."
        var node = find(t, afterType)

        if (node == null) {
            val decision = try {
                cloud.stepResult(StepResultRequest(flowId, step.index, false, t,
                    UiTree.summary(root), "target not found"))
            } catch (e: Exception) {
                Log.w(TAG, "step-result failed", e); null
            }
            Log.i(TAG, "Recovery decision: ${decision?.decision} ${decision?.message}")
            if (decision != null) {
                val proposed = decision.target
                when (decision.decision) {
                    "CONTINUE" -> return null
                    "STOP" -> return stop(decision.message)
                    "ASK_USER" -> return "⚠️ ${decision.message}"
                    // Cloud only proposes; Android re-validates the target exists on screen.
                    "RETRY_WITH_TARGET" -> node = proposed?.let { TargetResolver.resolve(root, it) }
                    "DISMISS_POPUP" -> {
                        val closeBtn = proposed?.let { TargetResolver.resolve(root, it) }
                        if (closeBtn != null) { ex.click(closeBtn); settle() }
                        node = find(t, false)
                    }
                }
            }
            if (node == null) {
                val what = t.text ?: t.contentDescription ?: "the input field"
                return "⚠️ Stuck at step ${step.index + 1}: I can't find '$what' on this screen."
            }
        }

        when (step.type) {
            "CLICK" -> {
                SafetyGate.sensitiveNode(node)?.let { return stop("Your turn — I don't tap '$it'.") }
                if (!ex.click(node)) return "⚠️ Step ${step.index + 1}: the tap didn't work."
            }
            "TYPE" -> {
                if (node.isPassword) return stop("Your turn — that's a password field.")
                if (!ex.type(node, step.value ?: "")) return "⚠️ Step ${step.index + 1}: couldn't type."
            }
        }
        settle()
        return null
    }

    /** Waits for loading, tries the keyboard's search key after typing, then scrolls. */
    private suspend fun find(t: Target, afterType: Boolean): AccessibilityNodeInfo? {
        var enterTried = !afterType
        for (attempt in 0 until 7) {
            TargetResolver.resolve(root, t)?.let { return it }
            if (attempt < 2) { delay(800); continue }
            if (!enterTried) { enterTried = true; ex.enter(root); settle(); continue }
            if (!ex.scrollForward(root)) break
            settle()
        }
        return null
    }

    private fun stop(msg: String): String {
        svc.overlay.show(msg, "OK") { svc.overlay.hide() }
        return "🛑 $msg"
    }

    private suspend fun settle(minMs: Long = 500, maxMs: Long = 4000) {
        val start = SystemClock.uptimeMillis()
        delay(minMs)
        while (SystemClock.uptimeMillis() - start < maxMs) {
            if (SystemClock.uptimeMillis() - svc.lastEventAt > 600) return
            delay(150)
        }
    }

    private suspend fun waitFor(timeoutMs: Long, cond: () -> Boolean): Boolean {
        val start = SystemClock.uptimeMillis()
        while (SystemClock.uptimeMillis() - start < timeoutMs) {
            if (cond()) return true
            delay(300)
        }
        return false
    }

    private fun describe(s: Step) = when (s.type) {
        "TYPE" -> "type '${s.value}'"
        "CLICK" -> "tap '${s.target?.text ?: s.target?.contentDescription ?: "…"}'"
        else -> s.type.lowercase()
    }

    companion object { const val TAG = "VoiceFlow" }
}
