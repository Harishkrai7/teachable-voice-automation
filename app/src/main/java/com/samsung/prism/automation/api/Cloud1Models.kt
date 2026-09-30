package com.samsung.prism.automation.api

import com.google.gson.annotations.SerializedName

data class Action(
    @SerializedName("action") val action: String,
    @SerializedName("target") val target: String? = null,
    @SerializedName("value") val value: String? = null
)

data class TeachRequest(
    @SerializedName("mode") val mode: String = "TEACH",
    @SerializedName("utterance") val utterance: String,
    @SerializedName("actions") val actions: List<Action>,
    @SerializedName("app") val app: String
)

data class ReplayRequest(
    @SerializedName("mode") val mode: String = "REPLAY",
    @SerializedName("utterance") val utterance: String,
    @SerializedName("currentApp") val currentApp: String
)

data class Slots(
    @SerializedName("restaurant") val restaurant: String?,
    @SerializedName("item") val item: String?,
    @SerializedName("quantity") val quantity: Int?,
    @SerializedName("address") val address: String?
)

data class Flow(
    @SerializedName("flowId") val flowId: String,
    @SerializedName("intent") val intent: String,
    @SerializedName("app") val app: String,
    @SerializedName("slots") val slots: Slots?,
    @SerializedName("steps") val steps: List<Action>?,
    @SerializedName("stopBefore") val stopBefore: List<String>?
)

data class ProcessResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("type") val type: String?,
    @SerializedName("mode") val mode: String?,
    @SerializedName("flow") val flow: Flow?,
    @SerializedName("flowId") val flowId: String?,
    @SerializedName("intent") val intent: String?,
    @SerializedName("slots") val slots: Slots?,
    @SerializedName("actions") val actions: List<Action>?,
    @SerializedName("question") val question: String?,
    @SerializedName("message") val message: String?,
    @SerializedName("reason") val reason: String?
)

data class ErrorResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("error") val error: ErrorDetail?
)

data class ErrorDetail(
    @SerializedName("code") val code: String,
    @SerializedName("message") val message: String
)

data class ReplayFailureFeedback(
    @SerializedName("flowId") val flowId: String,
    @SerializedName("actionIndex") val actionIndex: Int,
    @SerializedName("failedAction") val failedAction: Action,
    @SerializedName("reason") val reason: String,
    @SerializedName("currentApp") val currentApp: String
)

data class FeedbackResponse(
    @SerializedName("status") val status: String,
    @SerializedName("flowId") val flowId: String,
    @SerializedName("actionIndex") val actionIndex: Int,
    @SerializedName("reason") val reason: String
)
