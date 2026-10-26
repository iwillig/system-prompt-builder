ECA integration
===============

System Prompt Builder can render an ECA agent prompt and preserve the prompt
release metadata needed to identify that prompt in an evaluation artifact.

Render a prompt for ECA
-----------------------

Declare ECA as a harness in ``.spb/config.yaml``. List only the ECA tools that
the prompt should be told to use.

.. code-block:: yaml

   support-harness:
     - eca

   tool-provider-metadata:
     eca:
       tools: []

Render the prompt:

.. code-block:: console

   $ spb render prompts/coder.md --harness eca
   build/eca/coder.md

Use the rendered artifact in an ECA agent configuration. ECA documents the
``prompts.chat`` file reference as its custom agent prompt interface.

.. code-block:: json

   {
     "agent": {
       "spb": {
         "inherit": "code",
         "prompts": {
           "chat": "${file:/absolute/path/to/build/eca/coder.md}"
         }
       }
     }
   }

OpenTelemetry metrics
---------------------

ECA exports OpenTelemetry metrics when its ``otlp`` configuration is set. Add
the following to ECA's configuration, replacing the endpoint environment
variable with the endpoint for the team's OTLP collector:

.. code-block:: json

   {
     "otlp": {
       "otel.exporter.otlp.metrics.protocol": "http/protobuf",
       "otel.exporter.otlp.metrics.endpoint": "${env:OTEL_EXPORTER_OTLP_METRICS_ENDPOINT}",
       "otel.resource.attributes": "service.name=eca,service.namespace=system-prompt-builder"
     }
   }

If the collector requires authentication, configure
``otel.exporter.otlp.headers`` through ECA's environment-variable substitution.
Do not store credentials in the project configuration.

ECA's native integration exports metrics about ECA features. It does not emit
OpenTelemetry traces for ``spb`` CLI commands. Correlate ECA metrics with a
specific prompt release through the rendered prompt manifest, which records the
prompt version and rendered SHA-256 digest.

Sources
-------

* `ECA metrics configuration <https://eca.dev/config/metrics/>`_
* `ECA custom agent prompts <https://eca.dev/config/agents/>`_
