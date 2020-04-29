Pages HTML
===========

Flask General principles
-------------------------

Flask templates
.................

Flask templates are based on Jinja.

They are often called at the end of a route
using the function :py:func:`flask.render_template`. Template variables are defined
in this function call. Its results are often the route return. EG:

::

    @blueprint.route("/", methods=["GET", "POST"])
    def administration():
    var = 'Lorem Ipsum'
    return render_template(
        "administration.html", conf=current_app.config, var=var
    )


Flask templating format can be found in Flask documentation `Templates <https://flask.palletsprojects.com/en/1.1.x/tutorial/templates/>`_

Static files
.............

Static files such as css and js files go into ``collectives/static`` folder.

.. warning::

    Any CAF or FFCAM material (images, etc), must be placed into ``collectives/static/caf``
    to clarify licensing.

To create a URL to a static files, please use :py:func:`url_for`. EG ``{{ url_for('static', filename='css/administration.css') }}``

Collectives use of templates
-----------------------------

Template standard usage
.........................

Most pages have an associated template file in ``collectives/templates/``. Usually,
all templates are embedded within ``collectives/templates/base.html`` which sets html architecture,
``<head>``, header and footer.

Thus to create a new page, create a template file which extends from ``base.html`` using
``{% extends 'base.html' %}`` at the beginning of the file.

Additionnal ``<head>`` tags can be included by adding a block ``additionalhead``. EG:

::

    {% block additionalhead %}
      <link rel="stylesheet" href="{{ url_for('static', filename='css/administration.css') }}">

      {# DateTime picker#}
      <link rel="stylesheet" href="{{ url_for('static', filename='css/tail.datetime-harx-light.min.css') }}">
      <script src="{{ url_for('static', filename='js/tail.datetime-full.min.js') }}"></script>
    {% endblock %}

You shall define a title by adding blocks ``header`` and ``title``:

::

    {% block header %}
      <h1>{% block title %}TITRE{% endblock %}</h1>
    {% endblock %}

At last, your page content can be defined in a block ``content``.

::

    {% block content %}
    {% endblock %}

As an example for your templates, you may have a look at ``index.html``.


Jinja Macros
.........................

See `Jinja documentation about Macro <https://jinja.palletsprojects.com/en/2.11.x/templates/#macros>`_

Macro are used as functions to automatize repetitive block through the site. They are
defined in ``collectives/templates/macros.html``.

Helpers
.........................

 See `Flask documentation about context processor <https://flask.palletsprojects.com/en/1.1.x/templating/#context-processors>`_

Jinja uses its own set of functions. To add a useful function to Jinja template, you have to add it
to :py:func:`collectives.context_processor.helpers_processor`.



Ready to use Templates
-----------------------------

Simple forms
.............
For very simple forms with no need for advanced tuning, you can use the templates
``basicform.html``.

In :py:func:`flask.render_template` function call, send a :py:class:`flask_wtf.FlaskForm`
object and a title. The template will basically display all fields and add a submission
button.

EG

::

    def update_user():

        form = UserForm(obj=current_user)

        return render_template(
            "basicform.html",
            conf=current_app.config,
            form=form,
            title="Profil adhérent",
        )

As an example to use ``basicform.html``, you may have a look at :py:func:`collectives.routes.profile.update_user`.
