#!/usr/bin/env bash


reasonchip serve							\
	--log-level DEBUG						\
	--amqp-url ${AMQP_URL}					\
	--amqp-queue reasonchip					\
	--collection chatbot=./workflows

