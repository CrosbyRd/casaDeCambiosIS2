# core/management/commands/export_models_dot.py
from django.core.management.base import BaseCommand
from django.apps import apps
import re

class Command(BaseCommand):
    help = 'Exports Django model information to Graphviz DOT format.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Path to the output .dot file.',
            default='models.dot'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        dot_content = 'digraph models {\n'
        dot_content += '  rankdir=LR;\n' # Opcional: Left-to-Right layout
        dot_content += '  node [shape=record];\n\n'

        model_definitions = []
        relationship_definitions = []

        # Obtén el nombre de la app actual donde reside este comando
        # Esto se hace de forma más dinámica y robusta
        current_app_label = self.__module__.split('.')[0]
        for app_config in apps.get_app_configs():
            # Filtro común: excluir apps de Django y algunas otras que no queremos modelar
            # Corregido: Se cerró la lista con ']' y el paréntesis del 'if'
            if app_config.name.startswith('django.') or app_config.label in ['admin', 'sessions', 'contenttypes', 'auth']:
                 continue

            # Si quieres incluir específicamente las apps tuyas:
            # apps_propias = ['CasaDeCambioIS2', 'clientes', 'monedas', 'usuarios', 'roles', 'core', 'admin_panel', 'correo', 'cotizaciones', 'lib']
            # if app_config.label not in apps_propias:
            #     continue

            for model in app_config.get_models():
                model_name = model.__name__
                # Usa el label de la app_config para el nodo_id
                node_id = f"{app_config.label}_{model_name}"
                
                # Definición del nodo del modelo
                fields_str = f"{{ {model_name} |"
                field_names = []
                for field in model._meta.get_fields():
                    field_name = field.name
                    field_type = field.get_internal_type()
                    
                    # Añadir información sobre relaciones
                    if field.is_relation:
                        related_model = field.related_model
                        if related_model:
                            related_node_id = f"{related_model._meta.app_label}_{related_model.__name__}"
                            relationship_label = f"{field_name}"
                            if field.many_to_one:
                                relationship_label += " (FK)"
                            elif field.one_to_many:
                                relationship_label += " (OneToMany)"
                            elif field.many_to_many:
                                relationship_label += " (ManyToMany)"
                            elif field.one_to_one:
                                relationship_label += " (OneToOne)"

                            # Corregido: Se cerró el corchete ']' de la definición de la relación
                            relationship_definitions.append(
                                f'  "{node_id}" -> "{related_node_id}" [label="{relationship_label}"];'
                            )
                    
                    field_names.append(field_name)
                fields_str += " \\l".join(field_names) + " \\l" # \\l para alinear a la izquierda
                fields_str += "}}"
                model_definitions.append(f'  "{node_id}" [label="{fields_str}"];')

        dot_content += "\n".join(model_definitions) + "\n\n"
        dot_content += "\n".join(relationship_definitions) + "\n"
        dot_content += '}'

        try:
            with open(output_file, 'w') as f:
                f.write(dot_content)
            self.stdout.write(self.style.SUCCESS(f'Successfully exported model schema to {output_file}'))
        except IOError as e:
            self.stderr.write(self.style.ERROR(f'Error writing to file {output_file}: {e}'))
