"""One explicitly ordered inventory; no raw note/tag values are fetched."""
import os, json, re
from collections import Counter
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q, Case, When, Value, CharField
from crm.models import Organization, Person, OrganizationTenantAssignment, PersonTenantAssignment, Tag
from crm.services.domain_read_shadow import DOMAIN, TENANTS, TENANT_IDS, _require_scope
from crm.services.domain_backfill import database_identity


def inventory(expected, baseline):
    if not re.fullmatch('[0-9a-f]{40}', baseline): raise RuntimeError('CODE_CONTEXT')
    if connection.vendor != 'postgresql' or connection.in_atomic_block or not connection.get_autocommit():
        raise RuntimeError('TRANSACTION_CONTEXT')
    with transaction.atomic(durable=True):
        with connection.cursor() as c:
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            c.execute("SET LOCAL statement_timeout='30s'")
            c.execute("SET LOCAL lock_timeout='2s'")
        identity=database_identity()
        if identity != expected: raise RuntimeError('DATABASE_MISMATCH')
        _require_scope()
        def marker():
            with connection.cursor() as c:
                c.execute("SELECT pg_current_snapshot()::text,clock_timestamp(),current_setting('transaction_isolation'),current_setting('transaction_read_only')")
                return c.fetchone()
        start=marker(); results=[]; deviations=Counter(); all_tag_ids=set()
        for model, assignment, field in ((Organization,OrganizationTenantAssignment,'organization'),(Person,PersonTenantAssignment,'person')):
            pool=model.objects.filter(Q(tenant_id__in=TENANT_IDS)|Q(sharing_domain_id=1))
            profiles=list(pool.annotate(note_kind=Case(When(note__isnull=True,then=Value('null')),
                When(note='',then=Value('empty')),When(note__regex=r'^\s+$',then=Value('whitespace')),
                default=Value('text'),output_field=CharField())).values('id','tenant_id','sharing_domain_id','note_kind'))
            assignments=list(assignment.objects.filter(Q(tenant_id__in=TENANT_IDS)|Q(**{field+'__in':pool})).values(
                'tenant_id','tenant__sharing_domain_id',field+'_id',field+'__tenant_id',field+'__sharing_domain_id'))
            by_profile={}
            for a in assignments:
                by_profile.setdefault(a[field+'_id'],[]).append(a)
                if a['tenant__sharing_domain_id']!=1 or a[field+'__sharing_domain_id']!=1:
                    deviations['assignment_domain_mismatch']+=1
                if a['tenant_id'] not in TENANT_IDS or a[field+'__tenant_id'] not in TENANT_IDS:
                    deviations['assignment_scope_mismatch']+=1
                if a['tenant_id']!=a[field+'__tenant_id']:
                    deviations['nonlegacy_assignment']+=1
            through=model.tags.through
            links=list(through.objects.filter(Q(**{field+'__in':pool})|Q(tag__tenant_id__in=TENANT_IDS)).values(
                'tag_id','tag__tenant_id','tag__tenant__sharing_domain_id',field+'_id',field+'__tenant_id',field+'__sharing_domain_id',
                **({'published':django.db.models.F(field+'__is_published')} if model is Organization else {})))
            for link in links:
                all_tag_ids.add(link['tag_id'])
                if link['tag__tenant_id']!=link[field+'__tenant_id']:
                    deviations['tag_cross_tenant_link']+=1
                if link['tag__tenant__sharing_domain_id']!=1 or link[field+'__sharing_domain_id'] not in (None,1):
                    deviations['tag_domain_mismatch']+=1
                if link[field+'__tenant_id'] not in TENANT_IDS:
                    deviations['tag_profile_outside_scope']+=1
            for tenant in TENANT_IDS:
                selected=[p for p in profiles if p['tenant_id']==tenant]
                counts=Counter(p['note_kind'] for p in selected)
                eligible=missing=extra=wrong=null_domain=wrong_domain=0
                for p in selected:
                    rows=by_profile.get(p['id'],[])
                    own=[a for a in rows if a['tenant_id']==tenant and a['tenant__sharing_domain_id']==1 and a[field+'__sharing_domain_id']==1]
                    null_domain+=p['sharing_domain_id'] is None
                    wrong_domain+=p['sharing_domain_id'] not in (None,1)
                    missing+=not own
                    extra+=max(len(rows)-1,0)
                    wrong+=any(a not in own for a in rows)
                    eligible+=p['sharing_domain_id']==1 and len(rows)==len(own)==1
                scoped_links=[l for l in links if l[field+'__tenant_id']==tenant]
                used=Counter(l['tag_id'] for l in scoped_links)
                results.append({'model':model.__name__,'tenant_id':tenant,'profiles':len(selected),
                    'notes':{kind:counts[kind] for kind in ('null','empty','whitespace','text')},
                    'null_domain':null_domain,'wrong_domain':wrong_domain,'missing_own_assignment':missing,
                    'extra_assignments':extra,'profiles_with_wrong_assignment':wrong,'eligible_own_assignment':eligible,
                    'tag_links':len(scoped_links),'distinct_linked_tags':len(used),
                    'tags_used_by_multiple_profiles':sum(n>1 for n in used.values()),
                    'published_actor_tag_links':sum(bool(l.get('published')) for l in scoped_links)})
            deviations['profile_outside_legacy_scope']+=sum(p['tenant_id'] not in TENANT_IDS for p in profiles)
        tags=list(Tag.objects.filter(Q(tenant_id__in=TENANT_IDS)|Q(pk__in=all_tag_ids)).values('id','tenant_id','tenant__sharing_domain_id'))
        tag_counts=[{'tenant_id':t,'tag_rows':sum(x['tenant_id']==t for x in tags),
            'unused_tags':sum(x['tenant_id']==t and x['id'] not in all_tag_ids for x in tags)} for t in TENANT_IDS]
        deviations['tag_rows_outside_scope']+=sum(x['tenant_id'] not in TENANT_IDS or x['tenant__sharing_domain_id']!=1 for x in tags)
        end=marker()
        if start[0]!=end[0] or start[2:]!=('repeatable read','on') or end[2:]!=start[2:]:
            raise RuntimeError('SNAPSHOT_MISMATCH')
        return {'inventory_version':1,'code_baseline':baseline,'database_identity':identity,'domain':DOMAIN,
            'tenants':[{'id':i,'slug':s,'name':n} for i,s,n in TENANTS],'snapshot':start[0],
            'started_at':start[1].isoformat(),'ended_at':end[1].isoformat(),'read_only':True,'isolation':start[2],
            'overlay_gate':getattr(settings,'TENANT_NOTE_OVERLAYS_ENABLED',False),'rows':results,
            'tags':tag_counts,'deviations':{k:v for k,v in deviations.items() if v},'completed_rows':len(results)}

if __name__=='__main__':
    import sys
    try:
        result=inventory(sys.argv[1],sys.argv[2])
    except BaseException:
        print(json.dumps({'status':'INCOMPLETE','reason':'INVENTORY_FAILED'}));sys.exit(4)
    print(json.dumps(result,sort_keys=True))
