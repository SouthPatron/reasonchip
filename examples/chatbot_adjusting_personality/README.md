# Chatbot with mirroring personality

This is a chatbot which mirrors the user's personality and maintains
the current personality and message history in Redis/Valkey.

## How to run:

First, update your `_params.yml` and `_secrets.yml` to reflect your needs.

Then just run, making sure to set your OpenAI credentials.

<pre><code>

bash$ export OPENAI\_API\_KEY='<your openapi key>'
bash$ export OPENAI\_ORG\_ID='<your openapi organisational id>'

bash$ ./chat.sh

</code></pre>

