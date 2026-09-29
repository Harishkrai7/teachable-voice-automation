package com.prism.voiceflow

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Build
import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.math.abs

/**
 * Finds the intended element on the CURRENT screen from a semantic Target.
 * Priority: resourceId (+label) -> exact/normalised text -> content description ->
 * fuzzy text -> bounds (last resort, only when there is no label and no id).
 */
object TargetResolver {

    fun resolve(root: AccessibilityNodeInfo?, t: Target): AccessibilityNodeInfo? {
        if (root == null) return null
        val nodes = UiTree.visible(root)

        if (t.editable) {
            val eds = nodes.filter { it.isEditable && !it.isPassword }
            return eds.firstOrNull { t.resourceId != null && it.viewIdResourceName == t.resourceId }
                ?: eds.firstOrNull { it.isFocused }
                ?: eds.firstOrNull()
        }

        val label = t.text ?: t.contentDescription

        if (!t.textIsTemplate && t.resourceId != null) {
            val byId = nodes.filter { it.viewIdResourceName == t.resourceId }
            if (byId.size == 1 && (label == null || score(byId[0], label) >= 0.6)) return byId[0]
            if (byId.size > 1 && label != null) {
                val best = byId.maxByOrNull { score(it, label) }
                if (best != null && score(best, label) >= 0.8) return best
            }
        }

        if (label != null) {
            val threshold = if (t.textIsTemplate) 0.8 else 0.85
            return nodes.asSequence()
                .filter { !it.isEditable }
                .map { it to score(it, label) + bonus(it, t) }
                .filter { it.second >= threshold }
                .maxByOrNull { it.second }?.first
        }

        val b = t.bounds ?: return null
        if (b.size != 4) return null
        return nodes.firstOrNull { n ->
            val r = UiTree.bounds(n)
            n.isClickable && abs(r.left - b[0]) < 30 && abs(r.top - b[1]) < 30 &&
                abs(r.right - b[2]) < 30 && abs(r.bottom - b[3]) < 30
        }
    }

    private fun score(n: AccessibilityNodeInfo, label: String) = maxOf(
        TextUtil.similarity(n.text, label), TextUtil.similarity(n.contentDescription, label))

    private fun bonus(n: AccessibilityNodeInfo, t: Target): Double {
        var b = 0.0
        if (t.resourceId != null && n.viewIdResourceName == t.resourceId) b += 0.05
        if (t.className != null && n.className?.toString() == t.className) b += 0.02
        return b
    }
}

/** Performs actions through Accessibility APIs only (no app APIs, no deep links). */
class ActionExecutor(private val svc: AccessibilityService) {

    suspend fun click(node: AccessibilityNodeInfo): Boolean {
        var n: AccessibilityNodeInfo? = node
        while (n != null && !n.isClickable) n = n.parent
        if (n != null && n.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
        val r = UiTree.bounds(node)
        return tap(r.exactCenterX(), r.exactCenterY())
    }

    suspend fun tap(x: Float, y: Float): Boolean = suspendCancellableCoroutine { cont ->
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 60)).build()
        val ok = svc.dispatchGesture(gesture, object : AccessibilityService.GestureResultCallback() {
            override fun onCompleted(d: GestureDescription?) { if (cont.isActive) cont.resume(true) }
            override fun onCancelled(d: GestureDescription?) { if (cont.isActive) cont.resume(false) }
        }, null)
        if (!ok && cont.isActive) cont.resume(false)
    }

    fun type(node: AccessibilityNodeInfo, text: String): Boolean {
        node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    /** Presses the keyboard's search/enter key on the focused field (Android 11+). */
    fun enter(root: AccessibilityNodeInfo?): Boolean {
        if (root == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return false
        val f = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return false
        return f.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_IME_ENTER.id)
    }

    fun back() = svc.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK)

    fun scrollForward(root: AccessibilityNodeInfo?): Boolean {
        val scrollable = UiTree.visible(root).filter { it.isScrollable }
            .maxByOrNull { UiTree.bounds(it).let { r -> r.width() * r.height() } } ?: return false
        return scrollable.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
    }
}
