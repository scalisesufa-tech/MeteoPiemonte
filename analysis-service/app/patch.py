from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    import logging
    logging.error(f"Validation Error: {exc.errors()} Body: {exc.body}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
