package com.samsung.prism.automation

import android.view.accessibility.AccessibilityEvent
import android.util.Log

object ActionInterpreter {

    private const val TAG = "ActionInterpreter"

    fun interpret(event: AccessibilityEvent, node: UiNode?): ConcreteAction? {
        if (node == null) return null

        val eventType = event.eventType
        val className = node.className?.lowercase() ?: ""
        val text = node.text ?: ""
        val desc = node.contentDescription?.lowercase() ?: ""
        val resId = node.resourceId?.lowercase() ?: ""

        val isEditable = className.contains("edittext") || eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
        val isClickable = node.clickable || eventType == AccessibilityEvent.TYPE_VIEW_CLICKED

        // Safety check
        if (isSensitive(text, desc, resId, className)) {
            Log.w(TAG, "Sensitive interaction detected. Masking action.")
            return ConcreteAction(
                action = "SENSITIVE_ACTION_BLOCKED",
                target = "REDACTED",
                value = "REDACTED",
                packageName = node.packageName,
                timestamp = System.currentTimeMillis()
            )
        }

        // Search or Type Text
        if (isEditable && eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) {
            val isSearch = desc.contains("search") || resId.contains("search") || text.lowercase().contains("search")
            return ConcreteAction(
                action = if (isSearch) "SEARCH" else "TYPE_TEXT",
                target = desc.ifEmpty { resId.ifEmpty { "input_field" } },
                value = text,
                packageName = node.packageName,
                timestamp = System.currentTimeMillis()
            )
        }

        // Clicks / Selects / Quantity
        if (eventType == AccessibilityEvent.TYPE_VIEW_CLICKED) {
            
            // Check for quantity (e.g. increase/decrease)
            if (desc.contains("quantity") || desc.contains("increase") || desc.contains("decrease") || text.matches(Regex("^[0-9]+$"))) {
                return ConcreteAction(
                    action = "SET_QUANTITY",
                    target = desc.ifEmpty { resId },
                    value = text.ifEmpty { "1" },
                    packageName = node.packageName,
                    timestamp = System.currentTimeMillis()
                )
            }

            // Check for Add to cart
            if (text.lowercase().contains("add to cart") || desc.contains("cart")) {
                return ConcreteAction(
                    action = "ADD_TO_CART",
                    target = text.ifEmpty { desc },
                    packageName = node.packageName,
                    timestamp = System.currentTimeMillis()
                )
            }

            // Check for Select
            if (text.isNotEmpty() || desc.isNotEmpty()) {
                return ConcreteAction(
                    action = "SELECT",
                    target = text.ifEmpty { desc },
                    packageName = node.packageName,
                    timestamp = System.currentTimeMillis()
                )
            }
            
            // Generic click
            return ConcreteAction(
                action = "CLICK",
                target = resId.ifEmpty { "unknown_node" },
                packageName = node.packageName,
                timestamp = System.currentTimeMillis()
            )
        }

        // Scroll
        if (eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
            return ConcreteAction(
                action = "SCROLL",
                target = resId.ifEmpty { className },
                packageName = node.packageName,
                timestamp = System.currentTimeMillis()
            )
        }

        return null
    }

    private fun isSensitive(text: String, desc: String, resId: String, className: String): Boolean {
        val sensitiveKeywords = listOf("password", "pin", "otp", "cvv", "credit card", "payment", "auth")
        val combined = "$text $desc $resId $className".lowercase()
        return sensitiveKeywords.any { combined.contains(it) }
    }
}
