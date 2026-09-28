package com.samsung.prism.automation

import android.util.Log

object TeachSessionManager {
    private const val TAG = "TeachSessionManager"

    private var teaching = false
    private val actionList = mutableListOf<ConcreteAction>()
    private var currentPackage: String? = null

    fun startSession() {
        teaching = true
        actionList.clear()
        currentPackage = null
        Log.d(TAG, "Teach Session STARTED")
    }

    fun stopSession(): List<ConcreteAction> {
        teaching = false
        Log.d(TAG, "Teach Session STOPPED. Captured ${actionList.size} actions.")
        return actionList.toList()
    }

    fun isTeaching(): Boolean = teaching

    fun recordAction(action: ConcreteAction) {
        if (!teaching) return

        if (action.action == "SENSITIVE_ACTION_BLOCKED") {
            Log.w(TAG, "Ignoring sensitive action recording.")
            return
        }

        if (currentPackage == null && action.packageName != null) {
            currentPackage = action.packageName
        } else if (currentPackage != null && action.packageName != null && currentPackage != action.packageName) {
            Log.w(TAG, "Package switched from $currentPackage to ${action.packageName}. Actions might be unrelated.")
            // Could pause teaching here, but for now we just log it based on requirements.
        }

        // Deduplication Logic
        if (actionList.isNotEmpty()) {
            val last = actionList.last()
            
            // Text change debounce: If typing in the same field, just update the last action
            if ((action.action == "SEARCH" || action.action == "TYPE_TEXT") && 
                last.action == action.action && 
                last.target == action.target) {
                
                // Replace last action with updated value
                actionList[actionList.size - 1] = action
                Log.d(TAG, "Updated action: $action")
                return
            }
            
            // Ignore rapid duplicate clicks on same target
            if (action.action == "SELECT" && last.action == "SELECT" && last.target == action.target) {
                val timeDiff = (action.timestamp ?: 0L) - (last.timestamp ?: 0L)
                if (timeDiff < 1000) { // 1 second debounce for clicks
                    Log.d(TAG, "Debounced duplicate SELECT")
                    return
                }
            }
        }

        actionList.add(action)
        Log.d(TAG, "Recorded action: $action")
    }

    fun getActions(): List<ConcreteAction> = actionList.toList()

    fun clear() {
        actionList.clear()
        currentPackage = null
    }

    fun getCurrentPackage(): String? = currentPackage
}
