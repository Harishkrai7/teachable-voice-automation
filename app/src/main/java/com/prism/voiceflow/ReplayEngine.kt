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
class ReplayEngine(
    private val svc: VoiceFlowService,
    private val cloud: CloudClient
) {

    private val ex
        get() = svc.executor

    private val root: AccessibilityNodeInfo?
        get() = svc.rootInActiveWindow

    private fun status(msg: String) {
        Log.i(TAG, msg)
        svc.overlay.show(
            msg,
            "Stop"
        ) {
            svc.cancelReplay()
        }
    }

    suspend fun run(
        plan: ReplayResponse
    ): String {

        val app = plan.app
            ?: return "âš ï¸ Plan has no app."

        val launch =
            svc.packageManager.getLaunchIntentForPackage(app)
                ?: return "âš ï¸ $app is not installed."

        status("Opening appâ€¦")

        launch.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_CLEAR_TASK
        )

        svc.startActivity(launch)

        if (
            !waitFor(12_000) {
                root?.packageName?.toString() == app
            }
        ) {
            return "âš ï¸ Couldn't open $app."
        }

        settle(
            minMs = 2000,
            maxMs = 5000
        )

        val total = plan.steps.size
        var prevWasType = false

        for (step in plan.steps) {

            for (
                r in 0 until maxOf(
                    1,
                    step.repeat
                )
            ) {

                val rep =
                    if (step.repeat > 1) {
                        " (${r + 1}/${step.repeat})"
                    } else {
                        ""
                    }

                status(
                    "Step ${step.index + 1}/$total: " +
                        "${describe(step)}$rep"
                )

                doStep(
                    plan.flowId ?: "",
                    step,
                    prevWasType && r == 0
                )?.let {
                    return it
                }
            }

            prevWasType = step.type == "TYPE"
        }

        return "âœ… Done: all $total steps. I stopped before payment â€” your turn to review and pay."
    }

    /**
     * Returns null on success, or a user-facing message
     * describing where/why it stopped.
     */
    private suspend fun doStep(
        flowId: String,
        step: Step,
        afterType: Boolean
    ): String? {

        SafetyGate.sensitiveScreen(root)?.let {
            return stop(
                "Your turn â€” this screen needs you ($it)."
            )
        }

        when (step.type) {

            "BACK" -> {
                ex.back()
                settle()
                return null
            }

            "ENTER" -> {
                ex.enter(root)
                settle()
                return null
            }

            "SCROLL" -> {
                ex.scrollForward(root)
                settle()
                return null
            }
        }

        val t = step.target
            ?: return "âš ï¸ Step ${step.index + 1} has no target."

        var node = find(
            t = t,
            afterType = afterType,
            stepType = step.type,
            taughtTargetText = step.taughtTargetText,
            targetIsSlotResolved = step.targetIsSlotResolved
        )

        /*
         * For TYPE/SEARCH: if no editable field was found yet,
         * try tapping a clickable hint node.
         *
         * Many apps (e.g. Zomato) show the search bar as a
         * non-editable clickable TextView (a fake placeholder)
         * that opens a real EditText only after being tapped.
         */
        if (
            node == null &&
            (
                step.type == "TYPE" ||
                    step.type == "SEARCH"
                )
        ) {

            val hintNode =
                UiTree.visible(root).firstOrNull { n ->

                    !n.isEditable &&
                        n.isClickable &&
                        (
                            (
                                t.resourceId != null &&
                                    n.viewIdResourceName ==
                                    t.resourceId
                            ) ||
                                (
                                    t.text != null &&
                                        TextUtil.similarity(
                                            n.text,
                                            t.text
                                        ) >= 0.7
                                ) ||
                                (
                                    t.contentDescription != null &&
                                        TextUtil.similarity(
                                            n.contentDescription,
                                            t.contentDescription
                                        ) >= 0.7
                                )
                        )
                }

            if (hintNode != null) {

                Log.i(
                    TAG,
                    "Tapping hint node '" +
                        "${UiTree.ownLabel(hintNode)}' " +
                        "to open editor for step " +
                        "${step.index + 1}"
                )

                ex.click(hintNode)

                settle(
                    minMs = 800,
                    maxMs = 2500
                )

                node = find(
                    t = t,
                    afterType = false,
                    stepType = step.type,
                    taughtTargetText = step.taughtTargetText,
                    targetIsSlotResolved =
                        step.targetIsSlotResolved
                )
            }
        }

        if (node == null) {

            val decision =
                try {
                    cloud.stepResult(
                        StepResultRequest(
                            flowId,
                            step.index,
                            false,
                            t,
                            UiTree.summary(root),
                            "target not found"
                        )
                    )
                } catch (e: Exception) {
                    Log.w(
                        TAG,
                        "step-result failed",
                        e
                    )
                    null
                }

            Log.i(
                TAG,
                "Recovery decision: " +
                    "${decision?.decision} " +
                    "${decision?.message}"
            )

            if (decision != null) {

                val proposed = decision.target

                when (decision.decision) {

                    "CONTINUE" -> {
                        return null
                    }

                    "STOP" -> {
                        return stop(
                            decision.message
                        )
                    }

                    "ASK_USER" -> {
                        return "âš ï¸ ${decision.message}"
                    }

                    /*
                     * Cloud only proposes; Android re-validates
                     * the target exists on screen.
                     */
                    "RETRY_WITH_TARGET" -> {
                        node = proposed?.let {
                            TargetResolver.resolve(
                                root,
                                it,
                                step.taughtTargetText,
                                step.targetIsSlotResolved
                            )
                        }
                    }

                    "DISMISS_POPUP" -> {

                        val closeBtn =
                            proposed?.let {
                                TargetResolver.resolve(
                                    root,
                                    it,
                                    step.taughtTargetText,
                                    step.targetIsSlotResolved
                                )
                            }

                        if (closeBtn != null) {
                            ex.click(closeBtn)
                            settle()
                        }

                        node = find(
                            t = t,
                            afterType = false,
                            stepType = step.type,
                            taughtTargetText =
                                step.taughtTargetText,
                            targetIsSlotResolved =
                                step.targetIsSlotResolved
                        )
                    }
                }
            }

            if (node == null) {

                val what =
                    t.text
                        ?: t.contentDescription
                        ?: "the input field"

                return "âš ï¸ Stuck at step " +
                    "${step.index + 1}: " +
                    "I can't find '$what' on this screen."
            }
        }

        when (step.type) {

            "CLICK" -> {

                SafetyGate.sensitiveNode(node)?.let {
                    return stop(
                        "Your turn â€” I don't tap '$it'."
                    )
                }

                if (!ex.click(node)) {
                    return "âš ï¸ Step ${step.index + 1}: the tap didn't work."
                }
            }

            "TYPE" -> {

                if (node.isPassword) {
                    return stop(
                        "Your turn â€” that's a password field."
                    )
                }

                if (
                    !ex.type(
                        node,
                        step.value ?: ""
                    )
                ) {
                    return "âš ï¸ Step ${step.index + 1}: couldn't type."
                }
            }
        }

        settle()

        return null
    }

    /**
     * Waits for loading, tries the keyboard's search key
     * after typing, then scrolls.
     *
     * IMPORTANT:
     * TYPE and SEARCH steps NEVER scroll.
     * Scrolling cannot reveal a hidden text field â€” it only
     * destructively swipes horizontal carousels.
     *
     * For those steps we break out immediately after the
     * enter-key retry.
     */
    private suspend fun find(
        t: Target,
        afterType: Boolean,
        stepType: String = "CLICK",
        taughtTargetText: String? = null,
        targetIsSlotResolved: Boolean = false
    ): AccessibilityNodeInfo? {

        val isTextEntry =
            stepType == "TYPE" ||
                stepType == "SEARCH"

        var enterTried = !afterType

        for (attempt in 0 until 7) {

            TargetResolver.resolve(
                root,
                t,
                taughtTargetText,
                targetIsSlotResolved
            )?.let {
                return it
            }

            if (attempt < 2) {
                delay(800)
                continue
            }

            if (!enterTried) {
                enterTried = true
                ex.enter(root)
                settle()
                continue
            }

            /*
             * Never scroll to find a text input.
             * Scrolling swipes carousels, not reveals fields.
             */
            if (isTextEntry) {
                break
            }

            if (!ex.scrollForward(root)) {
                break
            }

            settle()
        }

        return null
    }

    private fun stop(msg: String): String {
        svc.overlay.show(
            msg,
            "OK"
        ) {
            svc.overlay.hide()
        }

        return "ðŸ›‘ $msg"
    }

    private suspend fun settle(
        minMs: Long = 500,
        maxMs: Long = 4000
    ) {

        val start =
            SystemClock.uptimeMillis()

        delay(minMs)

        while (
            SystemClock.uptimeMillis() - start <
                maxMs
        ) {

            if (
                SystemClock.uptimeMillis() -
                    svc.lastEventAt >
                    600
            ) {
                return
            }

            delay(150)
        }
    }

    private suspend fun waitFor(
        timeoutMs: Long,
        cond: () -> Boolean
    ): Boolean {

        val start =
            SystemClock.uptimeMillis()

        while (
            SystemClock.uptimeMillis() - start <
                timeoutMs
        ) {

            if (cond()) {
                return true
            }

            delay(300)
        }

        return false
    }

    private fun describe(
        s: Step
    ) = when (s.type) {

        "TYPE" ->
            "type '${s.value}'"

        "CLICK" ->
            "tap '${s.target?.text ?: s.target?.contentDescription ?: "â€¦"}'"

        else ->
            s.type.lowercase()
    }

    companion object {
        const val TAG = "VoiceFlow"
    }
}