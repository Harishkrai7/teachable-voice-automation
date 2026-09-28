package com.samsung.prism.automation

data class ConcreteAction(
    val action: String,
    val target: String? = null,
    val value: String? = null,
    val packageName: String? = null,
    val timestamp: Long? = null
)
