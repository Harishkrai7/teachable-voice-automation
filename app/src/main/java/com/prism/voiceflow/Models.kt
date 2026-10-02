package com.prism.voiceflow

// JSON contract v1.0 — keep in sync with backend/app/schemas.py.
// Every constructor parameter has a default so Gson uses the no-arg constructor
// and missing JSON fields get sane defaults instead of nulls in non-null fields.

data class Target(
    var resourceId: String? = null,
    var text: String? = null,
    var contentDescription: String? = null,
    var className: String? = null,
    var clickable: Boolean = false,
    var editable: Boolean = false,
    var isPassword: Boolean = false,
    var bounds: List<Int>? = null,
    var packageName: String? = null,
    var parentText: String? = null,
    var textIsTemplate: Boolean = false,
)

data class DemoAction(
    var type: String = "CLICK",
    var target: Target? = null,
    var value: String? = null,
    var repeat: Int = 1,
)

data class Step(
    var index: Int = 0,
    var type: String = "CLICK",
    var target: Target? = null,
    var value: String? = null,
    var repeat: Int = 1,
    var repeatSlot: String? = null,
    var repeatOffset: Int = 0,
    var taughtTargetText: String? = null,
    var targetIsSlotResolved: Boolean = false,
)

data class Flow(
    var flowId: String = "",
    var intent: String = "",
    var app: String = "",
    var slots: Map<String, Any?> = emptyMap(),
    var steps: List<Step> = emptyList(),
    var examples: List<String> = emptyList(),
    var stopBefore: List<String> = emptyList(),
    var createdAt: String = "",
)

data class TeachRequest(
    var utterance: String = "",
    var app: String = "",
    var actions: List<DemoAction> = emptyList(),
)

data class TeachResponse(
    var status: String = "",
    var message: String = "",
    var warnings: List<String> = emptyList(),
    var flow: Flow? = null,
)

data class ReplayRequest(
    var utterance: String = "",
    var currentApp: String? = null,
    var flowId: String? = null,
    var slotAnswers: Map<String, Any?> = emptyMap(),
)

data class Option(var flowId: String = "", var label: String = "")

data class ReplayResponse(
    var status: String = "",
    var message: String = "",
    var flowId: String? = null,
    var intent: String? = null,
    var app: String? = null,
    var slots: Map<String, Any?> = emptyMap(),
    var steps: List<Step> = emptyList(),
    var question: String? = null,
    var options: List<Option> = emptyList(),
    var missingSlot: String? = null,
    var stopBefore: List<String> = emptyList(),
)

data class ScreenSummary(
    var packageName: String? = null,
    var nodes: List<Target> = emptyList(),
    var screenTitle: String? = null,
)

data class StepResultRequest(
    var flowId: String = "",
    var stepIndex: Int = 0,
    var success: Boolean = false,
    var expected: Target? = null,
    var screen: ScreenSummary? = null,
    var error: String? = null,
)

data class StepResultResponse(
    var decision: String = "ASK_USER",
    var message: String = "",
    var target: Target? = null,
)
