# Hugging Face deployment

The assignment app is deployed at [MoustafaJarjour/second-story-studio](https://huggingface.co/spaces/MoustafaJarjour/second-story-studio). It was verified **Running on ZERO** on 17 October 2026, with successful live consultation and workshop answers.

[Verification evidence](demo/evidence/deployment.json) records the deployed revision and hosting hardware. The video includes the actual public Space and a real hosted reply.

## Current configuration

- Gradio SDK 6.30.0, Python 3.12, entry point `app.py`.
- `OPENAI_API_KEY` is a Space **Secret**. Never upload `.env`.
- `OPENAI_MODEL=gpt-4.1-mini` is a Space Variable.
- The Space hosts the interface; OpenAI provides model inference and the reflection call.
- For the existing ZeroGPU configuration, `app.py` registers an unused `@spaces.GPU(duration=1)` startup marker, disables automatic GPU wrapping, and never connects that function to a customer event. Chat and reflection do not request GPU work.

For a new deployment, upload the source and preserve `me/`. The root README includes Spaces metadata. Configure the Secret and Variable, then verify Running status and test a real question. Public visitors can consume the API credits of the server-side key when sending messages.

## Storage

Default Space runtime logs are ephemeral. They are not automatically pushed to GitHub or the Space's source repository. This submission includes only fictional-customer demonstration evidence under `demo/evidence/`. Normal local logs stay in the ignored `logs/` directory.

Official references: [Spaces configuration](https://huggingface.co/docs/hub/en/spaces-config-reference), [secrets and variables](https://huggingface.co/docs/hub/en/spaces-overview#managing-secrets-and-environment-variables), and [storage](https://huggingface.co/docs/hub/en/spaces-storage).
