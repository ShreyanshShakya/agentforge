import py_compile


def check_python_file(path):

    try:

        py_compile.compile(
            path,
            doraise=True
        )

        return True, None

    except Exception as e:

        return False, str(e)
