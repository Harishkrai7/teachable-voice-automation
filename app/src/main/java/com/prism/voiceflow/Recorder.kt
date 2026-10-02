package com.prism.voiceflow

import android.view.accessibility.AccessibilityNodeInfo

/**
 * Records meaningful actions while the user teaches:
 *  - clicks (repeated taps on the same control are merged into one step with repeat=N)
 *  - typed text (successive keystrokes in the same field are merged into one TYPE)
 * Scrolls and raw touches are ignored. Password fields are never recorded.
 */
class Recorder {
    var active = false
        private set
    var blocked = false // set when a sensitive screen appears; nothing more is recorded
    var utterance = ""
        private set
    var app: String? = null
        private set
    val actions = mutableListOf<DemoAction>()
    private var lastClickAt = 0L

    fun start(command: String) {
        utterance = command
        actions.clear()
        app = null
        blocked = false
        active = true
    }

    fun onClick(n: AccessibilityNodeInfo) {
        if (blocked) return
        val t = UiTree.toTarget(n)
        if (app == null) app = t.packageName
        val now = System.currentTimeMillis()
        val last = actions.lastOrNull()
        if (last != null && last.type == "CLICK" && sameTarget(last.target, t) && now - lastClickAt < 4000) {
            last.repeat += 1
        } else {
            actions.add(DemoAction(type = "CLICK", target = t))
        }
        lastClickAt = now
    }

    fun onTextChanged(n: AccessibilityNodeInfo, text: String) {
        if (blocked || n.isPassword) return
        val t = UiTree.toTarget(n)
        if (app == null) app = t.packageName
        val hint = n.hintText?.toString()
        val value = if (hint != null && text == hint) "" else text
        val last = actions.lastOrNull()
        if (last != null && last.type == "TYPE" && last.target?.resourceId == t.resourceId) {
            val prev = last.value ?: ""
            // Only update if the new text is a plausible user keystroke:
            // - shorter (user deleted characters), or
            // - a direct continuation (new text starts with what was already typed).
            // If the new text is LONGER but does NOT start with the previous value,
            // it is an autocomplete injection (e.g. Myntra filling "large black shirt"
            // after the user typed "black shirt") — IGNORE IT.
            val isUserEdit = value.length <= prev.length || value.startsWith(prev)
            if (isUserEdit) {
                last.value = value
            }
        } else {
            actions.add(DemoAction(type = "TYPE", target = t, value = value))
        }
    }

    fun stop(): TeachRequest? {
        active = false
        val cleaned = actions.filter { it.type != "TYPE" || !it.value.isNullOrBlank() }
        val pkg = app ?: return null
        if (cleaned.isEmpty()) return null
        return TeachRequest(utterance = utterance, app = pkg, actions = cleaned.toList())
    }

    fun cancel() {
        active = false
        actions.clear()
    }

    private fun sameTarget(a: Target?, b: Target?) =
        a != null && b != null && a.resourceId == b.resourceId && a.text == b.text &&
            a.contentDescription == b.contentDescription && a.bounds == b.bounds
}
