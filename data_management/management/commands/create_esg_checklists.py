from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from ...models.templates import ESGForm
from ...fixtures.esg_checklists import create_esg_checklists


class Command(BaseCommand):
    help = 'Creates the Environmental, Social, and Governance checklists'

    def add_arguments(self, parser):
        parser.add_argument('--env-form-id', type=int, help='ID of the Environmental form')
        parser.add_argument('--soc-form-id', type=int, help='ID of the Social form')
        parser.add_argument('--gov-form-id', type=int, help='ID of the Governance form')
        parser.add_argument('--list-forms', action='store_true', help='List available forms')

    def handle(self, *args, **options):
        if options['list_forms']:
            self.list_available_forms()
            return

        env_form_id = options['env_form_id']
        soc_form_id = options['soc_form_id']
        gov_form_id = options['gov_form_id']

        if not all([env_form_id, soc_form_id, gov_form_id]):
            self.stdout.write(self.style.WARNING(
                "You must provide all three form IDs. Use --list-forms to see available forms."
            ))
            return

        try:
            with transaction.atomic():
                env_checklist, soc_checklist, gov_checklist = create_esg_checklists(
                    env_form_id=env_form_id,
                    soc_form_id=soc_form_id,
                    gov_form_id=gov_form_id
                )

                if env_checklist and soc_checklist and gov_checklist:
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully created:\n"
                        f"- Environmental Checklist (ID: {env_checklist.id})\n"
                        f"- Social Checklist (ID: {soc_checklist.id})\n"
                        f"- Governance Checklist (ID: {gov_checklist.id})"
                    ))
                else:
                    self.stdout.write(self.style.ERROR("Failed to create checklists."))

        except Exception as e:
            raise CommandError(f"Error creating checklists: {e}")

    def list_available_forms(self):
        """List all available ESG forms to help the user choose form IDs."""
        forms = ESGForm.objects.all().order_by('name')

        if not forms.exists():
            self.stdout.write(self.style.WARNING("No ESG forms found. Please create forms first."))
            return

        self.stdout.write(self.style.SUCCESS("Available ESG Forms:"))
        for form in forms:
            self.stdout.write(f"ID: {form.id} - Name: {form.name} - Code: {form.code}")

        self.stdout.write("\nExample command:")
        self.stdout.write(
            "python manage.py create_esg_checklists --env-form-id=1 --soc-form-id=2 --gov-form-id=3"
        ) 