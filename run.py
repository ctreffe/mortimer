#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mortimer import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
