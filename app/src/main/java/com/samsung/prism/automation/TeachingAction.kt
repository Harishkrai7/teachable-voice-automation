package com.samsung.prism.automation

enum class ActionType {
    CLICK,
    TEXT_INPUT,
    SCROLL,
    BACK
}

/**
 * Represents a single user action captured by the Teaching Recorder.
 */
data class TeachingAction(
    val type: ActionType,
    val target: SemanticTarget?,
    val timestamp: Long,
    val metadata: Map<String, String> = emptyMap()
) {
    override fun toString(): String {
        return "TeachingAction(type=$type, time=$timestamp, target=$target)"
    }
}
