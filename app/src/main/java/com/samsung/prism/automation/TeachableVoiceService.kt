package com.samsung.prism.automation

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent

class TeachableVoiceService : AccessibilityService() {

    companion object {
        private const val TAG = "TeachableVoiceService"
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(TAG, "Teachable Voice Automation Service Connected.")
        ReplayEngine.attach(this)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        Log.d(TAG, "Received Accessibility Event: ${AccessibilityEvent.eventTypeToString(event.eventType)}")

        // For this milestone, we only process actions when teaching is active
        if (TeachSessionManager.isTeaching()) {
            val rootNode = rootInActiveWindow
            if (rootNode != null) {
                // To avoid parsing the whole tree if not needed, we can just look at the event node.
                // But since our ActionInterpreter expects a UiNode context, we will read the event source.
                val eventNodeInfo = event.source
                if (eventNodeInfo != null) {
                    val eventUiNode = UiTreeReader.readTree(eventNodeInfo)
                    if (eventUiNode != null) {
                        val concreteAction = ActionInterpreter.interpret(event, eventUiNode)
                        if (concreteAction != null) {
                            TeachSessionManager.recordAction(concreteAction)
                        }
                    }
                    eventNodeInfo.recycle()
                }
                rootNode.recycle() // Clean up root node
            }
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "Service Interrupted.")
    }
}
