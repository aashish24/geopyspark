"""Contains the various encoding/decoding methods to bring values to/from Python from Scala."""
import pickle
from functools import partial
import numpy as np
from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()

from geopyspark.geotrellis import (Extent, ProjectedExtent, TemporalProjectedExtent, SpatialKey,
                                   SpaceTimeKey, Tile)

from geopyspark.geotrellis.protobuf.tileMessages_pb2 import ProtoTile, ProtoMultibandTile, ProtoCellType
from geopyspark.geotrellis.protobuf import keyMessages_pb2
from geopyspark.geotrellis.protobuf import extentMessages_pb2
from geopyspark.geotrellis.protobuf import tupleMessages_pb2


_mapped_data_types = {
    0: 'BIT',
    1: 'BYTE',
    2: 'UBYTE',
    3: 'SHORT',
    4: 'USHORT',
    5: 'INT',
    6: 'FLOAT',
    7: 'DOUBLE'
}

# DECODERS


def from_pb_tile(tile, data_type=None):
    if not data_type:
        data_type = _mapped_data_types[tile.cellType.dataType]

    if data_type == 'BIT':
        cells = np.int8(tile.uint32Cells[:]).reshape(tile.rows, tile.cols)
    elif data_type == 'BYTE':
        cells = np.int8(tile.sint32Cells[:]).reshape(tile.rows, tile.cols)
    elif data_type == 'UBYTE':
        cells = np.uint8(tile.uint32Cells[:]).reshape(tile.rows, tile.cols)
    elif data_type == 'SHORT':
        cells = np.int16(tile.sint32Cells[:]).reshape(tile.rows, tile.cols)
    elif data_type == 'USHORT':
        cells = np.uint16(tile.uint32Cells[:]).reshape(tile.rows, tile.cols)
    elif data_type == 'INT':
        cells = np.int32(tile.sint32Cells[:]).reshape(tile.rows, tile.cols)
    elif data_type == 'FLOAT':
        cells = np.float32(tile.floatCells[:]).reshape(tile.rows, tile.cols)
    else:
        cells = np.double(tile.doubleCells[:]).reshape(tile.rows, tile.cols)

    return cells

def tile_decoder(proto_bytes):
    """Decodes a ``TILE`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :ref:`Tile <raster>`
    """

    tile = ProtoTile.FromString(proto_bytes)
    cell_type = _mapped_data_types[tile.cellType.dataType]
    cells = np.array([from_pb_tile(tile, cell_type)])

    if tile.cellType.hasNoData:
        return Tile(cells, cell_type, tile.cellType.nd)
    else:
        return Tile(cells, cell_type, None)

def from_pb_multibandtile(multibandtile):
    cell_type = _mapped_data_types[multibandtile.tiles[0].cellType.dataType]
    bands = np.array([from_pb_tile(tile, cell_type) for tile in multibandtile.tiles])

    if multibandtile.tiles[0].cellType.hasNoData:
        return Tile(bands, cell_type, multibandtile.tiles[0].cellType.nd)
    else:
        return Tile(bands, None, multibandtile.tiles[0].cellType.nd)

def multibandtile_decoder(proto_bytes):
    """Decodes a ``TILE`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :ref:`Tile <raster>`
    """

    return from_pb_multibandtile(ProtoMultibandTile.FromString(proto_bytes))

def from_pb_extent(pb_extent):
    """Creates an ``Extent`` from a ``ProtoExtent``.

    Args:
        pb_extent (:class:`~geopyspark.protobuf.extentMessages_pb2.ProtoExtent`): An instance
            of ``ProtoExtent``.

    Returns:
        :class:`~geopyspark.geotrellis.Extent`
    """

    return Extent(pb_extent.xmin, pb_extent.ymin, pb_extent.xmax, pb_extent.ymax)

def extent_decoder(proto_bytes):
    """Decodes an ``Extent`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :class:`~geopyspark.geotrellis.Extent`
    """

    pb_extent = extentMessages_pb2.ProtoExtent.FromString(proto_bytes)
    return from_pb_extent(pb_extent)

def from_pb_projected_extent(pb_projected_extent):
    """Creates a ``ProjectedExtent`` from a ``ProtoProjectedExtent``.

    Args:
        pb_projected_extent (:class:`~geopyspark.protobuf.extentMessages_pb2.ProtoProjectedExtent`):
            An instance of ``ProtoProjectedExtent``.

    Returns:
        :class:`~geopyspark.geotrellis.ProjectedExtent`
    """

    if pb_projected_extent.crs.epsg is not 0:
        return ProjectedExtent(extent=from_pb_extent(pb_projected_extent.extent),
                               epsg=pb_projected_extent.crs.epsg)
    else:
        return ProjectedExtent(extent=from_pb_extent(pb_projected_extent.extent),
                               proj4=pb_projected_extent.crs.proj4)

def projected_extent_decoder(proto_bytes):
    """Decodes a ``TemporalProjectedExtent`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :class:`~geopyspark.geotrellis.ProjectedExtent`
    """

    pb_projected_extent = extentMessages_pb2.ProtoProjectedExtent.FromString(proto_bytes)
    return from_pb_projected_extent(pb_projected_extent)

def from_pb_temporal_projected_extent(pb_temporal_projected_extent):
    """Creates a ``TemporalProjectedExtent`` from a ``ProtoTemporalProjectedExtent``.

    Args:
        pb_temporal_projected_extent (:class:`~geopyspark.protobuf.extentMessages_pb2.ProtoTemporalProjectedExtent`):
            An instance of ``ProtoTemporalProjectedExtent``.

    Returns:
        :class:`~geopyspark.geotrellis.TemporalProjectedExtent`
    """

    if pb_temporal_projected_extent.crs.epsg is not 0:
        return TemporalProjectedExtent(extent=from_pb_extent(pb_temporal_projected_extent.extent),
                                       epsg=pb_temporal_projected_extent.crs.epsg,
                                       instant=pb_temporal_projected_extent.instant)
    else:
        return TemporalProjectedExtent(extent=from_pb_extent(pb_temporal_projected_extent.extent),
                                       proj4=pb_temporal_projected_extent.crs.proj4,
                                       instant=pb_temporal_projected_extent.instant)

def temporal_projected_extent_decoder(proto_bytes):
    """Decodes a ``TemproalProjectedExtent`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :class:`~geopyspark.geotrellis.TemporalProjectedExtent`
    """

    pb_temporal_projected_extent = extentMessages_pb2.ProtoTemporalProjectedExtent.FromString(proto_bytes)
    return from_pb_temporal_projected_extent(pb_temporal_projected_extent)

def from_pb_spatial_key(pb_spatial_key):
    """Creates a ``SpatialKey`` from a ``ProtoSpatialKey``.

    Args:
        pb_spatial_key (:class:`~geopyspark.protobuf.keyMessages_pb2.ProtoSpatialKey`):
            An instance of ``ProtoSpatialKey``.

    Returns:
        :obj:`~geopyspark.geotrellis.SpatialKey`
    """

    return SpatialKey(col=pb_spatial_key.col, row=pb_spatial_key.row)

def spatial_key_decoder(proto_bytes):
    """Decodes a ``SpatialKey`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :obj:`~geopyspark.geotrellis.SpatialKey`
    """

    pb_spatial_key = keyMessages_pb2.ProtoSpatialKey.FromString(proto_bytes)
    return from_pb_spatial_key(pb_spatial_key)

def from_pb_space_time_key(pb_space_time_key):
    """Creates a ``SpaceTimeKey`` from a ``ProtoSpaceTimeKey``.

    Args:
        pb_space_time_key (:class:`~geopyspark.protobuf.keyMessages_pb2.ProtoSpaceTimeKey`):
            An instance of ``ProtoSpaceTimeKey``.

    Returns:
        :obj:`~geopyspark.geotrellis.SpaceTimeKey`
    """

    return SpaceTimeKey(col=pb_space_time_key.col, row=pb_space_time_key.row,
                        instant=pb_space_time_key.instant)

def space_time_key_decoder(proto_bytes):
    """Decodes a ``SpaceTimeKey`` into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :obj:`~geopyspark.geotrellis.SpaceTimeKey`
    """

    pb_space_time_key = keyMessages_pb2.ProtoSpaceTimeKey.FromString(proto_bytes)
    return from_pb_space_time_key(pb_space_time_key)

def tuple_decoder(proto_bytes, key_decoder):
    """Decodes a tuple into Python.

    Note:
        The value of the tuple is always assumed to be a :ref:`Tile <raster>`,
        thus, only the decoding method of the key is required.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.
        key_decoder (str): The name of the key type of the tuple.

    Returns:
        tuple
    """

    tup = tupleMessages_pb2.ProtoTuple.FromString(proto_bytes)
    multiband = from_pb_multibandtile(tup.tiles)

    if key_decoder == "ProjectedExtent":
        return (from_pb_projected_extent(tup.projectedExtent), multiband)
    elif key_decoder == "TemporalProjectedExtent":
        return (from_pb_temporal_projected_extent(tup.temporalProjectedExtent), multiband)
    elif key_decoder == "SpatialKey":
        return (from_pb_spatial_key(tup.spatialKey), multiband)
    else:
        return (from_pb_space_time_key(tup.spaceTimeKey), multiband)

def create_partial_tuple_decoder(key_type):
    """Creates a partial, tuple decoder function.

    Args:
        value_type (str): The type of the value in the tuple.

    Returns:
        A partial :meth:`~geopyspark.protobufregistry.ProtoBufRegistry.tuple_decoder`
        function that requires ``proto_bytes`` to execute.
    """

    return partial(tuple_decoder, key_decoder=key_type)

def image_rdd_decoder(proto_bytes, key_decoder):
    tup = tupleMessages_pb2.ProtoTuple.FromString(proto_bytes)
    image_bytes = tup.imageBytes

    if key_decoder == "ProjectedExtent":
        return (from_pb_projected_extent(tup.projectedExtent), image_bytes)
    elif key_decoder == "TemporalProjectedExtent":
        return (from_pb_temporal_projected_extent(tup.temporalProjectedExtent), image_bytes)
    elif key_decoder == "SpatialKey":
        return (from_pb_spatial_key(tup.spatialKey), image_bytes)
    else:
        return (from_pb_space_time_key(tup.spaceTimeKey), image_bytes)

def create_partial_image_rdd_decoder(key_type):
    return partial(image_rdd_decoder, key_decoder=key_type)

def _get_decoder(name):
    if name == "Tile":
        return tile_decoder
    elif name == "MultibandTile":
        return multibandtile_decoder
    elif name == 'ProjectedExtent':
        return projected_extent_decoder
    elif name == 'TemporalProjectedExtent':
        return temporal_projected_extent_decoder
    elif name == "SpatialKey":
        return spatial_key_decoder
    elif name == "SpaceTimeKey":
        return space_time_key_decoder
    else:
        raise Exception("Could not find value type that matches", name)


# ENCODERS

def to_pb_tile(obj):
    cells = obj.cells
    data_type = obj.cell_type

    if len(cells.shape) > 2:
        (_, rows, cols) = cells.shape
    else:
        (rows, cols) = cells.shape

    tile = ProtoTile()
    cell_type = tile.cellType

    tile.cols = cols
    tile.rows = rows

    if obj.no_data_value:
        cell_type.hasNoData = True
        cell_type.nd = obj.no_data_value
    else:
        cell_type.hasNoData = False

    if data_type == "BIT":
        cell_type.dataType = ProtoCellType.BIT
        tile.uint32Cells.extend(cells.flatten().tolist())
    elif data_type == "BYTE":
        cell_type.dataType = ProtoCellType.BYTE
        tile.sint32Cells.extend(cells.flatten().tolist())
    elif data_type == "UBYTE":
        cell_type.dataType = ProtoCellType.UBYTE
        tile.uint32Cells.extend(cells.flatten().tolist())
    elif data_type == "SHORT":
        cell_type.dataType = ProtoCellType.SHORT
        tile.sint32Cells.extend(cells.flatten().tolist())
    elif data_type == "USHORT":
        cell_type.dataType = ProtoCellType.USHORT
        tile.uint32Cells.extend(cells.flatten().tolist())
    elif data_type == "INT":
        cell_type.dataType = ProtoCellType.INT
        tile.sint32Cells.extend(cells.flatten().tolist())
    elif data_type == "FLOAT":
        ctype = tile.cellType
        ctype.dataType = ProtoCellType.FLOAT
        tile.floatCells.extend(cells.flatten().tolist())
    else:
        cell_type.dataType = ProtoCellType.DOUBLE
        tile.doubleCells.extend(cells.flatten().tolist())

    return tile


def tile_encoder(obj):
    """Decodes a ``TILE`` into bytes.

    Args:
        obj (:ref:`Tile <raster>`): An instance of ``Extent``.

    Returns:
        bytes
    """

    return to_pb_tile(obj).SerializeToString()


def to_pb_multibandtile(obj):
    cells = obj.cells
    if cells.ndim == 2:
        cells = np.expand_dims(cells, 0)

    band_count = cells.shape[0]

    def create_tile(index):
        return Tile(cells[index, :, :], obj.cell_type, obj.no_data_value)

    multibandtile = ProtoMultibandTile()
    multibandtile.tiles.extend([to_pb_tile(create_tile(x)) for x in range(band_count)])

    return multibandtile

def multibandtile_encoder(obj):
    """Decodes a ``TILE`` into bytes.

    Args:
        obj (:ref:`Tile <raster>`): An instance of ``Extent``.

    Returns:
        bytes
    """

    return to_pb_multibandtile(obj).SerializeToString()

def to_pb_extent(obj):
    """Converts an instance of ``Extent`` to ``ProtoExtent``.

    Args:
        obj (:class:`~geopyspark.geotrellis.Extent`): An instance of ``Extent``.

    Returns:
        :class:`~geopyspark.protobuf.extentMessages_pb2.ProtoExtent`
    """

    ex = extentMessages_pb2.ProtoExtent()

    ex.xmin = obj.xmin
    ex.ymin = obj.ymin
    ex.xmax = obj.xmax
    ex.ymax = obj.ymax

    return ex

def extent_encoder(obj):
    """Encodes an ``Extent`` into bytes.

    Args:
        obj (:class:`~geopyspark.geotrellis.Extent`): An instance of ``Extent``.

    Returns:
        bytes
    """

    return to_pb_extent(obj).SerializeToString()

def to_pb_projected_extent(obj):
    """Converts an instance of ``ProjectedExtent`` to ``ProtoProjectedExtent``.

    Args:
        obj (:class:`~geopyspark.geotrellis.ProjectedExtent`): An instance of
            ``ProjectedExtent``.

    Returns:
        :class:`~geopyspark.protobuf.extentMessages_pb2.ProtoProjectedExtent`
    """

    pex = extentMessages_pb2.ProtoProjectedExtent()

    crs = extentMessages_pb2.ProtoCRS()
    ex = to_pb_extent(obj.extent)

    if obj.epsg:
        crs.epsg = obj.epsg
    else:
        crs.proj4 = obj.proj4

    pex.extent.CopyFrom(ex)
    pex.crs.CopyFrom(crs)

    return pex

def projected_extent_encoder(obj):
    """Encodes a ``ProjectedExtent`` into bytes.

    Args:
        obj (:class:`~geopyspark.geotrellis.ProjectedExtent`): An instance of
            ``ProjectedExtent``.

    Returns:
        bytes
    """

    return to_pb_projected_extent(obj).SerializeToString()

def to_pb_temporal_projected_extent(obj):
    """Converts an instance of ``TemporalProjectedExtent`` to ``ProtoTemporalProjectedExtent``.

    Args:
        obj (:class:`~geopyspark.geotrellis.TemporalProjectedExtent`): An instance of
            ``TemporalProjectedExtent``.

    Returns:
        :class:`~geopyspark.protobuf.extentMessages_pb2.ProtoTemporalProjectedExtent`
    """

    tpex = extentMessages_pb2.ProtoTemporalProjectedExtent()

    crs = extentMessages_pb2.ProtoCRS()
    ex = to_pb_extent(obj.extent)

    if obj.epsg:
        crs.epsg = obj.epsg
    else:
        crs.proj4 = obj.proj4

    tpex.extent.CopyFrom(ex)
    tpex.crs.CopyFrom(crs)
    tpex.instant = obj.instant

    return tpex

def temporal_projected_extent_encoder(obj):
    """Encodes a ``TemproalProjectedExtent`` into bytes.

    Args:
        obj (:class:`~geopyspark.geotrellis.TemporalProjectedExtent`): An instance of
            ``TemporalProjectedExtent``.

    Returns:
        bytes
    """

    return to_pb_temporal_projected_extent(obj).SerializeToString()

def to_pb_spatial_key(obj):
    """Converts an instance of ``SpatialKey`` to ``ProtoSpatialKey``.

    Args:
        obj (:obj:`~geopyspark.geotrellis.SpatialKey`): An instance of ``SpatialKey``.

    Returns:
        :class:`~geopyspark.protobuf.keyMessages_pb2.ProtoSpatialKey`
    """

    spatial_key = keyMessages_pb2.ProtoSpatialKey()

    spatial_key.col = obj.col
    spatial_key.row = obj.row

    return spatial_key

def spatial_key_encoder(obj):
    """Encodes a ``SpatialKey`` into bytes.

    Args:
        obj (:obj:`~geopyspark.geotrellis.SpatialKey`): An instance of ``SpatialKey``.

    Returns:
        bytes
    """

    return to_pb_spatial_key(obj).SerializeToString()

def to_pb_space_time_key(obj):
    """Converts an instance of ``SpaceTimeKey`` to ``ProtoSpaceTimeKey``.

    Args:
        obj (:obj:`~geopyspark.geotrellis.SpaceTimeKey`): An instance of ``SpaceTimeKey``.

    Returns:
        :class:`~geopyspark.protobuf.keyMessages_pb2.ProtoSpaceTimeKey`
    """

    space_time_key = keyMessages_pb2.ProtoSpaceTimeKey()

    space_time_key.col = obj.col
    space_time_key.row = obj.row
    space_time_key.instant = obj.instant

    return space_time_key

def space_time_key_encoder(obj):
    """Encodes a ``SpaceTimeKey`` into bytes.

    Args:
        obj (:obj:`~geopyspark.geotrellis.SpaceTimeKey`): An instance of ``SpaceTimeKey``.

    Returns:
        bytes
    """

    return to_pb_space_time_key(obj).SerializeToString()

def tuple_encoder(obj, key_encoder):
    """Encodes a tuple into bytes.

    Note:
        The value of the tuple is always assumed to be a :ref:`Tile <raster>`,
        thus, only the encoding method of the key is required.

    Args:
        obj (tuple): The tuple to encode.
        key_encoder (str): The name of the key type of the tuple.

    Returns:
       bytes
    """

    tup = tupleMessages_pb2.ProtoTuple()
    tup.tiles.CopyFrom(to_pb_multibandtile(obj[1]))

    if key_encoder == "ProjectedExtent":
        tup.projectedExtent.CopyFrom(to_pb_projected_extent(obj[0]))
    elif key_encoder == "TemporalProjectedExtent":
        tup.temporalProjectedExtent.CopyFrom(to_pb_temporal_projected_extent(obj[0]))
    elif key_encoder == "SpatialKey":
        tup.spatialKey.CopyFrom(to_pb_spatial_key(obj[0]))
    else:
        tup.spaceTimeKey = to_pb_space_time_key(obj[0])

    return tup.SerializeToString()

def create_partial_tuple_encoder(key_type):
    """Creates a partial, tuple encoder function.

    Args:
        key_type (str): The type of the key in the tuple.

    Returns:
        A partial :meth:`~geopyspark.protobufregistry.tuple_encoder` function that requires an
        obj to execute.
    """

    return partial(tuple_encoder, key_encoder=key_type)

def _get_encoder(name):
    if name == "Tile":
        return tile_encoder
    elif name == "MultibandTile":
        return multibandtile_encoder
    elif name == 'ProjectedExtent':
        return projected_extent_encoder
    elif name == 'TemporalProjectedExtent':
        return temporal_projected_extent_encoder
    elif name == "SpatialKey":
        return spatial_key_encoder
    elif name == "SpaceTimeKey":
        return space_time_key_encoder
    else:
        raise Exception("Could not find value type that matches", name)
