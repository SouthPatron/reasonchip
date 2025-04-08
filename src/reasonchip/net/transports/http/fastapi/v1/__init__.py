from .stream.stream import router as stream_router


def populate(app):
    app.include_router(
        stream_router,
        prefix='/v1/stream',
        tags=["Stream"]
    )

