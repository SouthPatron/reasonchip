#!/usr/bin/env bash

reasonchip run								\
	--log-level DEBUG						\
	--collection chatbot=./workflows		\
	chatbot.app.entry						\
	--set user_id=durand					\
	--set message="Hello, how are you?"
