package com.samsung.prism.automation

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class TeachableVoiceService : AccessibilityService() {

    companion object {
        private const val TAG = "TeachableVoiceService"

        // Basic sensitive field check (Person 1)
        fun isSensitive(node: AccessibilityNodeInfo): Boolean {
            if (node.isPassword) return true
            val viewId = node.viewIdResourceName?.lowercase() ?: ""
            val contentDesc = node.contentDescription?.toString()?.lowercase() ?: ""
            if (viewId.contains("password") || viewId.contains("pin") || viewId.contains("cvv")) return true
            if (contentDesc.contains("password") || contentDesc.contains("pin") || contentDesc.contains("cvv")) return true
            return false
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.e(TAG, "========== TEACHABLE VOICE SERVICE CONNECTED ==========")

        // Team: attach replay engine
        ReplayEngine.attach(this)

        // Person 1: start recording teaching actions
        TeachingRecorder.startRecording()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) {
            Log.e(TAG, "Received NULL accessibility event")
            return
        }

        // Only log meaningful events to avoid flooding logcat
        if (event.eventType != AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) {
            Log.e(TAG, "Accessibility Event: ${AccessibilityEvent.eventTypeToString(event.eventType)}")
        }

        // =========================================================
        // Person 1: DETECT USER CLICK ΓÇö capture SemanticTarget + TeachingAction
        // =========================================================
        if (event.eventType == AccessibilityEvent.TYPE_VIEW_CLICKED) {

            val clickedNode: AccessibilityNodeInfo? = event.source

            if (clickedNode == null) {
                Log.e(TAG, "CLICK detected, but event.source is NULL")
            } else {
                try {
                    Log.e(TAG, "========== USER CLICK DETECTED ==========")

                    val bounds = Rect()
                    clickedNode.getBoundsInScreen(bounds)

                    val isSensitiveField = isSensitive(clickedNode)

                    val semanticTarget = SemanticTarget(
                        resourceId = clickedNode.viewIdResourceName,
                        normalizedText = TextNormalizer.normalize(clickedNode.text?.toString()),
                        contentDescription = clickedNode.contentDescription?.toString(),
                        className = clickedNode.className?.toString(),
                        packageName = clickedNode.packageName?.toString(),
                        clickable = clickedNode.isClickable,
                        enabled = clickedNode.isEnabled,
                        bounds = bounds,
                        isSensitive = isSensitiveField
                    )

                    Log.e(TAG, "TARGET CAPTURED: $semanticTarget")

                    val action = TeachingAction(
                        type = ActionType.CLICK,
                        target = semanticTarget,
                        timestamp = System.currentTimeMillis()
                    )

                    TeachingRecorder.recordAction(action)

                    Log.e(TAG, "==========================================")

                } catch (e: Exception) {
                    Log.e(TAG, "Error reading clicked UI node", e)
                } finally {
                    clickedNode.recycle()
                }
            }
        }

        // =========================================================
        // Team: Process events through ActionInterpreter when teaching is active
        // (skips VIEW_CLICKED to avoid double-recording with Person 1 above)
        // =========================================================
        if (TeachSessionManager.isTeaching() && event.eventType != AccessibilityEvent.TYPE_VIEW_CLICKED) {
            val eventNodeInfo = event.source
            if (eventNodeInfo != null) {
                try {
                    val eventUiNode = UiTreeReader.readTree(eventNodeInfo)
                    if (eventUiNode != null) {
                        val concreteAction = ActionInterpreter.interpret(event, eventUiNode)
                        if (concreteAction != null) {
                            TeachSessionManager.recordAction(concreteAction)
                        }
                    }
                } finally {
                    eventNodeInfo.recycle()
                }
            }
        }

        // =========================================================
        // Person 1: READ CURRENT UI TREE
        // =========================================================
        val rootNode = rootInActiveWindow

        if (rootNode == null) {
            Log.e(TAG, "rootInActiveWindow is NULL")
            return
        }

        try {
            val uiTree = UiTreeReader.readTree(rootNode)

            // Log only on meaningful events so we don't spam logcat
            if (event.eventType != AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) {
                Log.e(TAG, "Reading UI Tree...")
                if (uiTree != null) {
                    Log.e(TAG, "UI Tree successfully read")
                } else {
                    Log.e(TAG, "UI Tree returned NULL")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error while reading UI Tree", e)
        } finally {
            rootNode.recycle()
        }
    }

    override fun onInterrupt() {
        Log.e(TAG, "========== TEACHABLE VOICE SERVICE INTERRUPTED ==========")
        TeachingRecorder.stopRecording()
    }
}
