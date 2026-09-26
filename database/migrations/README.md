Alembic owns the schema. From the backend directory, or inside the backend container:

```bash
alembic upgrade head
```

Revision `0001_initial` enables PostGIS and creates every table from the SQLAlchemy models, including `GEOGRAPHY(Point, 4326)` well coordinates and full-text indexes.

Do not create tables by hand.
