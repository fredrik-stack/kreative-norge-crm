"""Standalone synthetic Docker dump/restore test (not a live/Borg restore).
Run: python3 crm/test_phase6a2_restore.py
Uses existing images, a new private network/container, no existing volumes.
"""
import json
from pathlib import Path
import subprocess
import time
import uuid


def run(*args, input=None):
    result = subprocess.run(args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f"Synthetic test command failed: {args[0:3]}\n{result.stderr.decode()}")
    return result.stdout


def main():
    suffix = uuid.uuid4().hex[:12]
    name = f"kn-phase6a2-restore-{suffix}"
    network = f"{name}-net"
    root = Path(__file__).resolve().parents[1]
    source = "phase6a2_restore_source"
    restored = "phase6a2_restore_target"
    created_network = created_container = False

    def api(database, *command, input=None):
        return run("docker", "run", "-i", "--rm", "--pull=never", "--network", network,
                   "-v", f"{root}:/app:ro", "-e", f"DB_NAME={database}",
                   "-e", "DB_USER=synthetic", "-e", "DB_PASSWORD=synthetic",
                   "-e", f"DB_HOST={name}", "kreative-norge-crm-api:latest", *command, input=input)
    try:
        run("docker", "network", "create", network)
        created_network = True
        run("docker", "run", "-d", "--pull=never", "--name", name, "--network", network,
            "--label", "kn.test=phase6a2-synthetic-restore", "--tmpfs", "/var/lib/postgresql/data:rw", "-e", f"POSTGRES_DB={source}",
            "-e", "POSTGRES_USER=synthetic", "-e", "POSTGRES_PASSWORD=synthetic", "postgres:16")
        created_container = True
        deadline = time.monotonic()+30
        while True:
            result = subprocess.run(["docker", "exec", name, "pg_isready", "-U", "synthetic", "-d", source], capture_output=True)
            if result.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Synthetic PostgreSQL readiness timeout")
            time.sleep(.2)
        api(source, "python", "manage.py", "migrate", "--noinput")
        setup = '''
import django, json, tempfile
from pathlib import Path
django.setup()
from django.contrib.auth import get_user_model
from crm.models import Tenant, Organization, Person, PersonContact, OrganizationPerson, LegacyDomainBackfillBatch
from crm.services.domain_backfill import dry_run, apply_backfill, _snapshot
operator=get_user_model().objects.create_superuser(username="synthetic-restore", password="synthetic")
t=Tenant.objects.create(name="Synthetic Restore",slug="synthetic-restore")
o=Organization.objects.create(tenant=t,name="Synthetic",phone="raw",note="private",is_published=True)
p=Person.objects.create(tenant=t,full_name="Synthetic",phone="raw")
PersonContact.objects.create(tenant=t,person=p,type="EMAIL",value="synthetic@example.invalid")
OrganizationPerson.objects.create(tenant=t,organization=o,person=p)
mapping={"domain":{"id":None,"slug":"synthetic-domain","name":"Synthetic Domain"},"tenants":[{"id":t.pk,"slug":t.slug,"name":t.name}]}
plan=dry_run(mapping)
with tempfile.TemporaryDirectory() as private:
    apply_backfill(mapping=mapping,environment="synthetic",expected_database=plan["database_identity"],expected_digest=plan["plan"]["digest"],batch_id="restore",operator_id=operator.pk,code_baseline="a"*40,manifest_path=str(Path(private)/"prepared.json"))
print(json.dumps({"snapshot":_snapshot(),"batch":list(LegacyDomainBackfillBatch.objects.values())},default=str,sort_keys=True))
'''
        baseline = json.loads(api(source, "python", "-c", "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings';"+setup))
        dump = run("docker", "exec", name, "pg_dump", "-U", "synthetic", "-Fc", source)
        run("docker", "exec", name, "createdb", "-U", "synthetic", restored)
        run("docker", "exec", "-i", name, "pg_restore", "-U", "synthetic", "--exit-on-error", "-d", restored, input=dump)
        verify = '''
import django,json,sys
django.setup()
from django.db import connection,transaction,IntegrityError
from django.db.models.deletion import ProtectedError
from crm.models import Tenant,Person,PersonTenantAssignment,LegacyDomainBackfillBatch
from crm.domain_integrity import DomainStructureError
from crm.services.domain_backfill import _snapshot,database_identity
expected=json.loads(sys.stdin.read())
assert json.loads(json.dumps({"snapshot":_snapshot(),"batch":list(LegacyDomainBackfillBatch.objects.values())},default=str,sort_keys=True))==expected
with connection.cursor() as c:
    c.execute("SELECT count(*) FROM pg_trigger WHERE tgname IN ('crm_tenant_domain_guard','crm_organization_domain_guard','crm_person_domain_guard','crm_org_assignment_guard','crm_person_assignment_guard') AND tgenabled='O'")
    assert c.fetchone()[0]==5
for sql in ("UPDATE crm_person SET sharing_domain_id=NULL", "DELETE FROM crm_persontenantassignment"):
    try:
        with transaction.atomic():
            with connection.cursor() as c: c.execute(sql)
    except IntegrityError: pass
    else: raise AssertionError("Restored trigger did not protect state")
try: PersonTenantAssignment.objects.create(person=Person.objects.get(),tenant=Tenant.objects.get())
except DomainStructureError: pass
else: raise AssertionError("Restored ORM boundary bypassed")
try: Person.objects.get().delete()
except ProtectedError: pass
else: raise AssertionError("Restored parent protection bypassed")
assert LegacyDomainBackfillBatch.objects.get().database_identity != database_identity()
print(json.dumps({"restore":"PASS","state":"identical","active_triggers":5,"orm_and_sql_guards":"PASS","batch_original_identity_preserved":True}))
'''
        result = api(restored, "python", "-c", "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings';"+verify,
                     input=json.dumps(baseline).encode())
        print(result.decode().strip())
    finally:
        if created_container:
            run("docker", "rm", "-fv", name)
        if created_network:
            run("docker", "network", "rm", network)


if __name__ == "__main__":
    main()
