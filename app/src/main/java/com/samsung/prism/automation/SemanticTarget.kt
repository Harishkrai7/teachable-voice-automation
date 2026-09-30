package com.samsung.prism.automation

import android.graphics.Rect

/**
 * A persistent, serializable snapshot of a semantic target.
 * This model does not depend on AccessibilityNodeInfo directly,
 * making it safe to store and pass around.
 */
data class SemanticTarget(
    val resourceId: String?,
    val normalizedText: String?,
    val contentDescription: String?,
    val className: String?,
    val packageName: String?,
    val clickable: Boolean,
    val enabled: Boolean,
    val bounds: Rect,
    val isSensitive: Boolean = false
) {
    override fun toString(): String {
        return "SemanticTarget(id=$resourceId, text='$normalizedText', desc='$contentDescription', class=$className, pkg=$packageName, bounds=$bounds, sensitive=$isSensitive)"
    }
}
