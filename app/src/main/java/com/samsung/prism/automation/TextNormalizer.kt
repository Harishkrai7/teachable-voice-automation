package com.samsung.prism.automation

object TextNormalizer {
    /**
     * Safely normalizes visible text for semantic matching.
     * Trims leading/trailing whitespace, reduces repeated whitespaces,
     * and converts to lowercase.
     */
    fun normalize(text: String?): String? {
        if (text.isNullOrBlank()) return null
        return text.trim().replace(Regex("\\s+"), " ").lowercase()
    }
}
