# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError


def get_name(obj):
    return "%s_%s" % (obj._meta.model_name, obj.pk)

class Command(BaseCommand):
    help = (
        "verry simple command that will output a dot diagraph "
        "representing the current data of the database for a given app"
    )

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+')

    def handle(self, *app_labels, **options):

        from django.apps import apps
        try:
            app_configs = [apps.get_app_config(app_label) for app_label in app_labels]
        except (LookupError, ImportError) as e:
            raise CommandError("%s. Are you sure your INSTALLED_APPS setting is correct?" % e)
        # output something like this :
        # digraph my_graph {
        #     a -> b -> c;
        #     b -> d;
        # }
        #

        def node_generator():
            for app_config in app_configs: # type: django.apps.config.AppConfig
                for model in app_config.get_models(): # type: django.db.models.Model
                    if model.objects.count() > 100:
                        raise CommandError("to many items in the model %s to be effective. this commande is a bad idea on your app")
                    for obj in model.objects.all():
                        childs = []
                        for field in model._meta.get_fields():

                            if field.many_to_many:
                                childs.extend(list(getattr(obj, field.attname).all()))
                            elif field.many_to_one:
                                try:
                                    childs.append(getattr(obj, field.attname))
                                except field.related_model.DoesNotExist:
                                    pass
                        childs = [child for child in childs if child is not None]
                        yield (obj, childs)

        self.stdout.write(self.get_digraph(node_generator()))


    def get_digraph(self, objects):
        edges = []
        nodes={}
        for obj, childs in objects:
            nodes.setdefault(obj.__class__, []).append(obj)
            edges.append(get_name(obj))
            for child in childs:
                edges.append("%s  -> %s" % (get_name(obj), get_name(child)))
        return "digraph items_in_db {\n%s\n%s;\n}" % (
            "\n".join(
                ("{ rank=same; %s; }"% ";".join(map(get_name, objs)))
                for objs in nodes.values()
            ),
            ";\n".join(edges)
        )

