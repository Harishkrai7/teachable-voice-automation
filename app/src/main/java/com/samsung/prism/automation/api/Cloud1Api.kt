package com.samsung.prism.automation.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

interface Cloud1Api {
    @POST("/v1/process")
    suspend fun processTeach(@Body request: TeachRequest): Response<ProcessResponse>
    
    @POST("/v1/process")
    suspend fun processReplay(@Body request: ReplayRequest): Response<ProcessResponse>
    
    @POST("/v1/feedback")
    suspend fun sendFeedback(@Body feedback: ReplayFailureFeedback): Response<FeedbackResponse>
}
