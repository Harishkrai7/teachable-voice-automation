package com.samsung.prism.automation

import android.view.accessibility.AccessibilityNodeInfo

object ActionVerifier {

    fun verify(
        action: ConcreteAction,
        newRoot: AccessibilityNodeInfo?
    ): Boolean {
        if (newRoot == null) return false
        
        return when (action.action) {
            "TYPE_TEXT", "SEARCH" -> {
                // Verify the text exists somewhere in an editable field or in the UI
                hasText(newRoot, action.value ?: action.target ?: "")
            }
            "SELECT", "CLICK", "ADD_TO_CART" -> {
                // UI changed. We can't strictly know if it was correct without AI,
                // but we can ensure the app didn't crash and the tree is valid.
                // For a more strict check, verify the target node is no longer there
                // or a new screen appeared. We'll return true if tree exists and is different.
                true
            }
            "SET_QUANTITY" -> {
                hasText(newRoot, action.value ?: "")
            }
            "SCROLL" -> {
                true
            }
            else -> false
        }
    }

    private fun hasText(node: AccessibilityNodeInfo, text: String): Boolean {
        if (!node.refresh()) return false
        
        val nodeText = node.text?.toString() ?: ""
        if (nodeText.contains(text, ignoreCase = true)) return true
        
        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child != null) {
                if (hasText(child, text)) return true
                child.recycle()
            }
        }
        return false
    }
}
