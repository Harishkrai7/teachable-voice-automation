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
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        Log.d(TAG, "Received Accessibility Event: ${AccessibilityEvent.eventTypeToString(event.eventType)}")

        // For this milestone, we only read the UI tree without taking any automation actions.
        val rootNode = rootInActiveWindow
        if (rootNode != null) {
            Log.d(TAG, "Reading UI Tree...")
            val uiTree = UiTreeReader.readTree(rootNode)
            if (uiTree != null) {
                // Log the detected UI nodes for debugging
                UiTreeReader.logTree(uiTree)
            } else {
                Log.w(TAG, "Failed to read UI Tree (returned null)")
            }
            rootNode.recycle() // Clean up root node
        } else {
            Log.d(TAG, "rootInActiveWindow is null")
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "Service Interrupted.")
    }
}
