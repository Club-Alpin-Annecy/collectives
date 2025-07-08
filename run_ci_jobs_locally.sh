#!/bin/bash

PWD=`pwd`

run_black () {
 echo "***** RUN format *****"
 uvx ruff format
}

run_linter () {
 echo " ***** RUN linter *****"
 uvx ruff check
}

exec_tests () {
 echo " ***** EXEC Tests*****"
 uv run pytest --cov=collectives tests/ --cov-fail-under=60
}

build_html_doc () {
 echo " ***** BUILD Doc in $PWD/doc *****"
 cd $PWD/doc && uv run make html
}

check_doc_coverage_side_folders () {
 echo " ***** CHECK Doc coverage for side folders *****"
 cd $PWD && uv run docstr-coverage .  -e ".*(.env|.venv|migrations|instance|doc).*" -F 73
}

check_doc_coverage_models () {
 echo " ***** CHECK doc coverage on Models *****"
 cd $PWD && uv run docstr-coverage collectives/models
}

check_doc_coverage_utils () {
 echo " ***** CHECK doc coverage on Uils *****"
 cd $PWD && uv run docstr-coverage collectives/utils
}

check_doc_coverage_apis () {
 echo " ***** CHECK doc coverage on API *****"
 cd $PWD && uv run docstr-coverage collectives/api
}

check_doc_coverage_routes () {
 echo " ***** CHECK doc coverage on Routes *****"
 cd $PWD && uv run docstr-coverage collectives/routes
}

# catch first arguments with $1
case "$1" in
 -b|--black)
  run_black
  ;;
 -l|--linter)
  run_linter
  ;;
 -t|--tests)
  exec_tests
  ;;
 -h|--html)
  build_html_doc
  ;;
 -dc|--doc-coverage)
  check_doc_coverage_side_folders
  ;;
 -dm|--doc-coverage-models)
  check_doc_coverage_models
  ;;
 -du|--doc-coverage-utils)
  check_doc_coverage_utils
  ;;
 -da|--doc-coverage-api)
  check_doc_coverage_apis
  ;;
 -dr|--doc-coverage-routes)
  check_doc_coverage_routes
  ;;
 -a|--all)
  echo " ***** RUN ALL JOBS *****"
  run_black
  run_linter
  exec_tests
  check_doc_coverage_apis
  check_doc_coverage_models
  check_doc_coverage_routes
  check_doc_coverage_side_folders
  check_doc_coverage_utils
  build_html_doc
  ;;
  *)
  echo "Usage: (-b|--black -l|--linter -t|--tests -h|--html -dc|--doc-coverage -dm|--doc-coverage-models -du|--doc-coverage-utils -da|--doc-coverage-api -dr|--doc-coverage-routes -a|--all)"
  ;;
esac








