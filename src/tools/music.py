"""Music tools for the Music Store Assistant.

These are READ-ONLY tools for querying the music catalog.
Used by the Music_Expert node.
"""

from langchain_core.tools import tool
from src.utils import get_db


@tool
def get_albums_by_artist(artist: str) -> str:
    """Get all albums by a specific artist.

    Use this tool when a customer wants to know what albums are available
    from a particular artist. Supports partial/fuzzy matching.

    Args:
        artist: The artist name to search for (partial match supported).

    Returns:
        A formatted string of album titles and artist names.
    """
    db = get_db()
    return db.run(
        f"""
        SELECT Album.Title, Artist.Name 
        FROM Album 
        JOIN Artist ON Album.ArtistId = Artist.ArtistId 
        WHERE Artist.Name LIKE '%{artist}%';
        """,
        include_columns=True,
    )


@tool
def get_tracks_by_artist(artist: str) -> str:
    """Get all tracks/songs by a specific artist.

    Use this tool when a customer wants to know what songs are available
    from a particular artist. Returns song names with artist info.

    Args:
        artist: The artist name to search for (partial match supported).

    Returns:
        A formatted string of track names and artist names.
    """
    db = get_db()
    return db.run(
        f"""
        SELECT Track.Name as SongName, Artist.Name as ArtistName 
        FROM Album 
        LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId 
        LEFT JOIN Track ON Track.AlbumId = Album.AlbumId 
        WHERE Artist.Name LIKE '%{artist}%';
        """,
        include_columns=True,
    )


@tool
def check_for_songs(song_title: str) -> str:
    """Search for songs by title.

    Use this tool when a customer is looking for a specific song
    or wants to check if a song exists in the catalog.

    Args:
        song_title: The song title to search for (partial match supported).

    Returns:
        Track information including name, album, and duration.
    """
    db = get_db()
    return db.run(
        f"""
        SELECT Track.Name, Album.Title as AlbumTitle, Track.Milliseconds/1000 as DurationSeconds
        FROM Track
        JOIN Album ON Track.AlbumId = Album.AlbumId
        WHERE Track.Name LIKE '%{song_title}%'
        LIMIT 20;
        """,
        include_columns=True,
    )


@tool
def get_artists_by_genre(genre: str) -> str:
    """Get artists by genre/style of music.

    Use this tool when a customer asks about a genre like rock, jazz, metal, etc.
    Returns the top artists in that genre based on number of tracks in catalog.

    Args:
        genre: The genre to search for (e.g., "rock", "jazz", "metal", "blues").

    Returns:
        A list of top artists in that genre with their track counts.
    """
    db = get_db()
    return db.run(
        f"""
        SELECT Artist.Name as ArtistName, COUNT(*) as TrackCount
        FROM Genre
        JOIN Track ON Genre.GenreId = Track.GenreId
        JOIN Album ON Track.AlbumId = Album.AlbumId
        JOIN Artist ON Album.ArtistId = Artist.ArtistId
        WHERE Genre.Name LIKE '%{genre}%'
        GROUP BY Artist.Name
        ORDER BY TrackCount DESC
        LIMIT 15;
        """,
        include_columns=True,
    )


@tool
def list_genres() -> str:
    """List all available music genres in our catalog.

    Use this tool when a customer wants to know what genres/styles
    of music are available, or asks "what kind of music do you have?"

    Returns:
        A list of all genres available in the catalog.
    """
    db = get_db()
    return db.run(
        """
        SELECT Name FROM Genre ORDER BY Name;
        """,
        include_columns=True,
    )


# Export all music tools as a list for easy binding
MUSIC_TOOLS = [
    get_albums_by_artist,
    get_tracks_by_artist,
    check_for_songs,
    get_artists_by_genre,
    list_genres,
]
