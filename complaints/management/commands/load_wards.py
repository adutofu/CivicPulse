import os
from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from complaints.models import Ward

# Maps GeoPackage column names (left) to Django model field names (right).
# 'boundary': 'MULTIPOLYGON' tells LayerMapping which geometry type to expect
# from the source file's 'Shape' column.
ward_mapping = {
    'country': 'country',
    'iso3': 'iso3',
    'state': 'state',
    'statecode': 'statecode',
    'lga': 'lga',
    'ward': 'ward',
    'area_sqkm': 'area_sqkm',
    'boundary': 'MULTIPOLYGON',
}

# Absolute path to the GRID3 GeoPackage file downloaded from your colleague.
# One-time load — this path only needs to be valid on the machine running this command.
gpkg_path = '/home/raydev/Downloads/GRID3_NGA_operational_wards_v2_0.gpkg'

class Command(BaseCommand):
    help = 'Load Nigerian Ward boundaries from GRID3 GeoPackage into the Ward table'

    def handle(self, *args, **options):
        # transform=False because the source file is already SRID 4326 (WGS84),
        # matching our Ward.boundary field — no coordinate reprojection needed.
        lm = LayerMapping(Ward, gpkg_path, ward_mapping, transform=False)

        # strict=True stops the whole load on the first bad row rather than
        # silently skipping it — safer for a one-time data import like this.
        lm.save(strict=True, verbose=True)

        self.stdout.write(self.style.SUCCESS(f'Loaded {Ward.objects.count()} wards.'))