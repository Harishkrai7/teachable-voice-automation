package com.prism.voiceflow

import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo

/** Reads the accessibility tree and turns nodes into semantic Targets. */
object UiTree {

    fun all(root: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> {
        val out = ArrayList<AccessibilityNodeInfo>()
        fun rec(n: AccessibilityNodeInfo?, depth: Int) {
            if (n == null || depth > 60 || out.size > 2000) return
            out.add(n)
            for (i in 0 until n.childCount) rec(n.getChild(i), depth + 1)
        }
        rec(root, 0)
        return out
    }

    fun visible(root: AccessibilityNodeInfo?) = all(root).filter { it.isVisibleToUser }

    fun ownLabel(n: AccessibilityNodeInfo): String? =
        n.text?.toString()?.takeIf { it.isNotBlank() }
            ?: n.contentDescription?.toString()?.takeIf { it.isNotBlank() }

    /** Label of a node or, for containers (cards, rows), of its first labelled descendant. */
    fun deepLabel(n: AccessibilityNodeInfo, depth: Int = 0): String? {
        if (!n.isEditable) ownLabel(n)?.let { return it }
        if (depth >= 4) return null
        for (i in 0 until n.childCount) {
            val c = n.getChild(i) ?: continue
            deepLabel(c, depth + 1)?.let { return it }
        }
        return null
    }

    fun bounds(n: AccessibilityNodeInfo): Rect = Rect().also { n.getBoundsInScreen(it) }

    fun toTarget(n: AccessibilityNodeInfo): Target {
        val r = bounds(n)
        val desc = n.contentDescription?.toString()?.takeIf { it.isNotBlank() }
        val text = when {
            n.isEditable -> null // typed text is captured separately as the TYPE value
            !n.text.isNullOrBlank() -> n.text.toString()
            desc == null -> deepLabel(n)
            else -> null
        }
        return Target(
            resourceId = n.viewIdResourceName,
            text = text,
            contentDescription = desc,
            className = n.className?.toString(),
            clickable = n.isClickable,
            editable = n.isEditable,
            isPassword = n.isPassword,
            bounds = listOf(r.left, r.top, r.right, r.bottom),
            packageName = n.packageName?.toString(),
            parentText = n.parent?.let { ownLabel(it) },
        )
    }

    /** Compact screen description sent to Cloud when a step fails. Never includes typed secrets. */
    fun summary(root: AccessibilityNodeInfo?, max: Int = 150): ScreenSummary {
        val nodes = visible(root)
            .filter { ownLabel(it) != null || it.isClickable || it.isEditable }
            .take(max)
            .map { n ->
                toTarget(n).apply {
                    if (n.isEditable) text = if (n.isPassword) null else n.hintText?.toString()
                }
            }
        return ScreenSummary(root?.packageName?.toString(), nodes)
    }

    /** Milestone M1 inspector: human-readable dump for logcat. */
    fun dump(root: AccessibilityNodeInfo?): String {
        val sb = StringBuilder("package=${root?.packageName}\n")
        fun rec(n: AccessibilityNodeInfo?, depth: Int) {
            if (n == null || depth > 40) return
            if (n.isVisibleToUser) {
                val r = bounds(n)
                sb.append("  ".repeat(depth))
                    .append(n.className?.toString()?.substringAfterLast('.'))
                    .append(" text=").append(if (n.isPassword) "***" else n.text)
                    .append(" desc=").append(n.contentDescription)
                    .append(" id=").append(n.viewIdResourceName)
                    .append(if (n.isClickable) " [click]" else "")
                    .append(if (n.isEditable) " [edit]" else "")
                    .append(if (n.isScrollable) " [scroll]" else "")
                    .append(" ").append(r.toShortString()).append('\n')
            }
            for (i in 0 until n.childCount) rec(n.getChild(i), depth + 1)
        }
        rec(root, 0)
        return sb.toString()
    }
}
