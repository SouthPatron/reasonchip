#!/usr/bin/env bash


#	--log-level reasonchip.cli.commands.serve=DEBUG			\

reasonchip serve							\
	--log-level DEBUG						\
	--amqp-url ${AMQP_URL}					\
	--amqp-queue reasonchip					\
	--collection chatbot=./workflows
