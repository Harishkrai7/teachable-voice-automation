package com.samsung.prism.automation

object ReplaySessionManager {
    enum class State {
        IDLE, RUNNING, WAITING_FOR_UI, FAILED, COMPLETED, STOPPED
    }

    private var currentState = State.IDLE
    private var actions = listOf<ConcreteAction>()
    private var currentIndex = 0
    private var flowId: String? = null
    
    // For feedback
    var lastFailureReason: String? = null
    var failedAction: ConcreteAction? = null
    var currentApp: String? = null

    fun startReplay(fId: String, newActions: List<ConcreteAction>, app: String) {
        flowId = fId
        actions = newActions
        currentIndex = 0
        currentApp = app
        currentState = State.RUNNING
        lastFailureReason = null
        failedAction = null
    }

    fun stopReplay() {
        currentState = State.STOPPED
    }

    fun failReplay(reason: String, action: ConcreteAction? = null) {
        currentState = State.FAILED
        lastFailureReason = reason
        failedAction = action ?: getCurrentAction()
    }

    fun completeReplay() {
        currentState = State.COMPLETED
    }

    fun advanceAction() {
        currentIndex++
        if (currentIndex >= actions.size) {
            completeReplay()
        }
    }

    fun getCurrentAction(): ConcreteAction? {
        if (currentIndex < actions.size) return actions[currentIndex]
        return null
    }

    fun getCurrentIndex(): Int = currentIndex
    fun getTotalActions(): Int = actions.size
    fun getState(): State = currentState
    fun getFlowId(): String? = flowId
    
    fun setState(state: State) {
        if (currentState != State.FAILED && currentState != State.STOPPED) {
            currentState = state
        }
    }
}
