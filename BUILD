# https://github.com/bazelbuild/rules_python#consuming-pip-dependencies
load("@my_deps//:requirements.bzl", "requirement")

py_library(
    name = "solver_lib",
    srcs = ["solver_lib.py"],
    deps = [
	  requirement("absl-py"),
    ],
    data = [
        "dictionary.txt",
        "solutions.txt",
    ],
)

py_test(
    name = "solver_lib_test",
    srcs = ["solver_lib_test.py"],
    deps = [
	  ":solver_lib",
	  ":simulation",
	  requirement("absl-py"),
    ],
)

py_library(
    name = "simulation",
    srcs = ["simulation.py"],
    deps = [
      ":solver_lib",
    ],
)

py_test(
    name = "benchmark_test",
    srcs = ["benchmark_test.py"],
    deps = [
	  requirement("absl-py"),
      ":simulation",
    ],
    timeout = "eternal",
    tags = ["manual"],
)

py_binary(
    name = "wordle_solver",
    srcs = ["wordle_solver.py"],
    data = ["dictionary.txt"],
    deps = [
	  ":solver_lib",
	  requirement("absl-py"),
    ],
)
