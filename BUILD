# https://github.com/bazelbuild/rules_python#consuming-pip-dependencies
load("@my_deps//:requirements.bzl", "requirement")

# pytype_strict_binary(
py_binary(
    name = "wordle_solver",
    srcs = ["wordle_solver.py"],
    data = ["dictionary.txt"],
    deps = [
	requirement("absl-py"),
    ],
)
