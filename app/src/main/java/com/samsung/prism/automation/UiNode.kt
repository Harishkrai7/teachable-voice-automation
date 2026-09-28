package com.samsung.prism.automation

import android.graphics.Rect

/**
 * Semantic representation of a UI element extracted from the Accessibility tree.
 */
data class UiNode(
    val text: String?,
    val contentDescription: String?,
    val resourceId: String?,
    val className: String?,
    val packageName: String?,
    val clickable: Boolean,
    val enabled: Boolean,
    val bounds: Rect,
    val children: List<UiNode>
) {
    override fun toString(): String {
        return "UiNode(text=$text, desc=$contentDescription, resId=$resourceId, class=$className, pkg=$packageName, clickable=$clickable, bounds=${bounds.toShortString()}, childrenCount=${children.size})"
    }
}
