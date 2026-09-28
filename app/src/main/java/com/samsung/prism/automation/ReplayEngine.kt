package com.samsung.prism.automation

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import kotlinx.coroutines.*

object ReplayEngine {
    private const val TAG = "ReplayEngine"
    private const val ACTION_TIMEOUT_MS = 5000L

    private var service: AccessibilityService? = null
    private var job: Job? = null

    fun attach(accessibilityService: AccessibilityService) {
        service = accessibilityService
    }

    fun start() {
        if (ReplaySessionManager.getState() != ReplaySessionManager.State.RUNNING) return
        
        job?.cancel()
        job = CoroutineScope(Dispatchers.Default).launch {
            while (ReplaySessionManager.getState() == ReplaySessionManager.State.RUNNING) {
                val action = ReplaySessionManager.getCurrentAction()
                if (action == null) {
                    ReplaySessionManager.completeReplay()
                    break
                }
                
                // Sensitive Data Check
                if (isSensitive(action)) {
                    ReplaySessionManager.failReplay("SENSITIVE_ACTION", action)
                    break
                }

                // Verify App
                if (!verifyApp(action)) {
                    ReplaySessionManager.failReplay("WRONG_APPLICATION", action)
                    break
                }

                ReplaySessionManager.setState(ReplaySessionManager.State.WAITING_FOR_UI)
                val success = executeAction(action)
                
                if (success) {
                    // Wait for UI to settle
                    delay(1000)
                    
                    val root = service?.rootInActiveWindow
                    if (ActionVerifier.verify(action, root)) {
                        ReplaySessionManager.setState(ReplaySessionManager.State.RUNNING)
                        ReplaySessionManager.advanceAction()
                    } else {
                        ReplaySessionManager.failReplay("ACTION_VERIFICATION_FAILED", action)
                    }
                    root?.recycle()
                } else {
                    // ReplaySessionManager state already set to FAILED in executeAction
                }
            }
        }
    }

    fun stop() {
        job?.cancel()
        ReplaySessionManager.stopReplay()
    }

    private suspend fun executeAction(action: ConcreteAction): Boolean {
        return withTimeoutOrNull(ACTION_TIMEOUT_MS) {
            var node: AccessibilityNodeInfo? = null
            // Polling until node is found or timeout
            while (isActive) {
                val root = service?.rootInActiveWindow
                if (root != null) {
                    node = NodeMatcher.findBestMatch(root, action.target ?: "", action.action)
                    root.recycle()
                    if (node != null) break
                }
                delay(500)
            }

            if (node == null) {
                ReplaySessionManager.failReplay("NODE_NOT_FOUND", action)
                return@withTimeoutOrNull false
            }

            val success = performActionOnNode(node, action)
            node.recycle()
            if (!success) {
                ReplaySessionManager.failReplay("PERFORM_ACTION_FAILED", action)
            }
            success
        } ?: run {
            ReplaySessionManager.failReplay("UI_STATE_TIMEOUT", action)
            false
        }
    }

    private fun performActionOnNode(node: AccessibilityNodeInfo, action: ConcreteAction): Boolean {
        return when (action.action) {
            "SEARCH", "TYPE_TEXT" -> {
                val args = Bundle().apply {
                    putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, action.value ?: action.target)
                }
                node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
            }
            "SELECT", "CLICK", "ADD_TO_CART" -> {
                node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            }
            "SET_QUANTITY" -> {
                val args = Bundle().apply {
                    putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, action.value)
                }
                if (node.isEditable) {
                    node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
                } else {
                    node.performAction(AccessibilityNodeInfo.ACTION_CLICK) // Fallback for +/- buttons
                }
            }
            "SCROLL" -> {
                node.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
            }
            else -> false
        }
    }

    private fun isSensitive(action: ConcreteAction): Boolean {
        val keywords = listOf("password", "pin", "otp", "payment", "auth")
        val combined = "${action.action} ${action.target} ${action.value}".lowercase()
        return keywords.any { combined.contains(it) }
    }
    
    private fun verifyApp(action: ConcreteAction): Boolean {
        // Mock verification for now. In real life, we check current package.
        return true
    }
}
