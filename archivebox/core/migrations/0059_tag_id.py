# Generated by Django 5.0.6 on 2024-08-20 03:33

from datetime import datetime
from django.db import migrations, models
from archivebox.base_models.abid import abid_from_values
from archivebox.base_models.models import ABID

def calculate_abid(self):
    """
    Return a freshly derived ABID (assembled from attrs defined in ABIDModel.abid_*_src).
    """
    prefix = self.abid_prefix
    ts = eval(self.abid_ts_src)
    uri = eval(self.abid_uri_src)
    subtype = eval(self.abid_subtype_src)
    rand = eval(self.abid_rand_src)

    if (not prefix) or prefix == 'obj_':
        suggested_abid = self.__class__.__name__[:3].lower()
        raise Exception(f'{self.__class__.__name__}.abid_prefix must be defined to calculate ABIDs (suggested: {suggested_abid})')

    if not ts:
        ts = datetime.utcfromtimestamp(0)
        print(f'[!] WARNING: Generating ABID with ts=0000000000 placeholder because {self.__class__.__name__}.abid_ts_src={self.abid_ts_src} is unset!', ts.isoformat())

    if not uri:
        uri = str(self)
        print(f'[!] WARNING: Generating ABID with uri=str(self) placeholder because {self.__class__.__name__}.abid_uri_src={self.abid_uri_src} is unset!', uri)

    if not subtype:
        subtype = self.__class__.__name__
        print(f'[!] WARNING: Generating ABID with subtype={subtype} placeholder because {self.__class__.__name__}.abid_subtype_src={self.abid_subtype_src} is unset!', subtype)

    if not rand:
        rand = getattr(self, 'uuid', None) or getattr(self, 'id', None) or getattr(self, 'pk')
        print(f'[!] WARNING: Generating ABID with rand=self.id placeholder because {self.__class__.__name__}.abid_rand_src={self.abid_rand_src} is unset!', rand)

    abid = abid_from_values(
        prefix=prefix,
        ts=ts,
        uri=uri,
        subtype=subtype,
        rand=rand,
    )
    assert abid.ulid and abid.uuid and abid.typeid, f'Failed to calculate {prefix}_ABID for {self.__class__.__name__}'
    return abid


def update_archiveresult_ids(apps, schema_editor):
    Tag = apps.get_model("core", "Tag")
    num_total = Tag.objects.all().count()
    print(f'   Updating {num_total} Tag.id, ArchiveResult.uuid values in place...')
    for idx, tag in enumerate(Tag.objects.all().iterator(chunk_size=500)):
        if not tag.slug:
            tag.slug = tag.name.lower().replace(' ', '_')
        if not tag.name:
            tag.name = tag.slug
        if not (tag.name or tag.slug):
            tag.delete()
            continue

        assert tag.slug or tag.name, f'Tag.slug must be defined! You have a Tag(id={tag.pk}) missing a slug!'
        tag.abid_prefix = 'tag_'
        tag.abid_ts_src = 'self.created'
        tag.abid_uri_src = 'self.slug'
        tag.abid_subtype_src = '"03"'
        tag.abid_rand_src = 'self.old_id'
        tag.abid = calculate_abid(tag)
        tag.id = tag.abid.uuid
        tag.save(update_fields=["abid", "id", "name", "slug"])
        assert str(ABID.parse(tag.abid).uuid) == str(tag.id)
        if idx % 10 == 0:
            print(f'Migrated {idx}/{num_total} Tag objects...')



class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_alter_tag_old_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='tag',
            name='id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.RunPython(update_archiveresult_ids, reverse_code=migrations.RunPython.noop),
    ]
