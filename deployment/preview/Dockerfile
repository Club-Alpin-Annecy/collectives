# Image of a pull request preview: the image of the pull request, plus the test
# fixtures that tests/preview_seed.py loads in the database of the instance.
ARG PR_IMAGE
FROM ${PR_IMAGE}

COPY tests /app/tests/
RUN cd /app; uv sync --locked --extra deploy
