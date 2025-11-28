"""Tests for music tools (read-only catalog operations)."""

import pytest


def test_get_albums_by_artist_exists():
    """Music tools should have get_albums_by_artist function."""
    from src.tools.music import get_albums_by_artist
    
    assert get_albums_by_artist is not None


def test_get_tracks_by_artist_exists():
    """Music tools should have get_tracks_by_artist function."""
    from src.tools.music import get_tracks_by_artist
    
    assert get_tracks_by_artist is not None


def test_check_for_songs_exists():
    """Music tools should have check_for_songs function."""
    from src.tools.music import check_for_songs
    
    assert check_for_songs is not None


def test_get_artists_by_genre_exists():
    """Music tools should have get_artists_by_genre function."""
    from src.tools.music import get_artists_by_genre
    
    assert get_artists_by_genre is not None


def test_list_genres_exists():
    """Music tools should have list_genres function."""
    from src.tools.music import list_genres
    
    assert list_genres is not None


def test_get_albums_by_artist_is_tool():
    """get_albums_by_artist should be decorated as a LangChain tool."""
    from src.tools.music import get_albums_by_artist
    
    # LangChain tools have a 'name' attribute
    assert hasattr(get_albums_by_artist, "name"), "Should be a LangChain @tool"


def test_get_albums_by_artist_has_docstring():
    """Tools must have docstrings so the LLM knows when to use them."""
    from src.tools.music import get_albums_by_artist
    
    # LangChain tools expose description
    assert hasattr(get_albums_by_artist, "description")
    assert len(get_albums_by_artist.description) > 10, "Tool needs a meaningful docstring"


def test_get_artists_by_genre_is_tool():
    """get_artists_by_genre should be decorated as a LangChain tool."""
    from src.tools.music import get_artists_by_genre
    
    assert hasattr(get_artists_by_genre, "name"), "Should be a LangChain @tool"


def test_list_genres_is_tool():
    """list_genres should be decorated as a LangChain tool."""
    from src.tools.music import list_genres
    
    assert hasattr(list_genres, "name"), "Should be a LangChain @tool"


@pytest.mark.integration
def test_get_albums_by_artist_returns_results():
    """get_albums_by_artist should return album data from the database."""
    from src.tools.music import get_albums_by_artist
    
    # AC/DC is a known artist in Chinook
    result = get_albums_by_artist.invoke({"artist": "AC/DC"})
    
    assert result is not None
    assert "AC/DC" in result or "acdc" in result.lower()


@pytest.mark.integration
def test_get_tracks_by_artist_returns_results():
    """get_tracks_by_artist should return track data from the database."""
    from src.tools.music import get_tracks_by_artist
    
    result = get_tracks_by_artist.invoke({"artist": "AC/DC"})
    
    assert result is not None
    assert len(result) > 0


@pytest.mark.integration
def test_check_for_songs_returns_results():
    """check_for_songs should find songs by title."""
    from src.tools.music import check_for_songs
    
    # "For Those About To Rock" is a known track in Chinook
    result = check_for_songs.invoke({"song_title": "Rock"})
    
    assert result is not None
    assert len(result) > 0


@pytest.mark.integration
def test_get_artists_by_genre_returns_rock_artists():
    """get_artists_by_genre should return artists for a given genre."""
    from src.tools.music import get_artists_by_genre
    
    result = get_artists_by_genre.invoke({"genre": "Rock"})
    
    assert result is not None
    # Should contain known rock artists from Chinook
    assert "Led Zeppelin" in result or "U2" in result or "Deep Purple" in result


@pytest.mark.integration
def test_get_artists_by_genre_returns_metal_artists():
    """get_artists_by_genre should return metal artists."""
    from src.tools.music import get_artists_by_genre
    
    result = get_artists_by_genre.invoke({"genre": "Metal"})
    
    assert result is not None
    # Should contain known metal artists from Chinook
    assert "Metallica" in result or "Iron Maiden" in result or "Black Sabbath" in result


@pytest.mark.integration
def test_list_genres_returns_all_genres():
    """list_genres should return all available genres."""
    from src.tools.music import list_genres
    
    result = list_genres.invoke({})
    
    assert result is not None
    assert "Rock" in result
    assert "Jazz" in result
    assert "Metal" in result
    assert "Blues" in result


@pytest.mark.integration
def test_music_tools_list_includes_genre_tools():
    """MUSIC_TOOLS should include the new genre tools."""
    from src.tools.music import MUSIC_TOOLS, get_artists_by_genre, list_genres
    
    assert get_artists_by_genre in MUSIC_TOOLS
    assert list_genres in MUSIC_TOOLS
