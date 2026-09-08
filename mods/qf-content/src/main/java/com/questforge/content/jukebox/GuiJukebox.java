package com.questforge.content.jukebox;

import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.GuiTextField;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraft.util.EnumChatFormatting;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.GL11;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * The jukebox: search five catalogs, queue what you find, keep what you like.
 *
 * Everything is drawn by hand rather than assembled from GuiButton, because the
 * vanilla widgets carry a stone-texture look that fights the rest of the pack and
 * cannot show what these rows need to show -- artwork, two lines of text, and
 * controls that appear only under the cursor.
 *
 * Five views share one list: search results, the artists in them, playlists, saved
 * songs, and the queue. They differ only in what fills {@code rows}, so scrolling,
 * hovering, the row actions and the keyboard work identically in all of them.
 */
public class GuiJukebox extends GuiScreen {

    // Palette. Warm accent against cool neutrals, so the one thing that is
    // playing or selected is never in doubt.
    private static final int ACCENT       = 0xFFE0A34A;
    private static final int ACCENT_SOFT  = 0x33E0A34A;
    private static final int PANEL        = 0xF2101418;
    private static final int PANEL_EDGE   = 0xFF2B3238;
    private static final int FIELD        = 0xFF171C21;
    private static final int RULE         = 0xFF232A30;
    private static final int TEXT         = 0xFFE8ECF0;
    private static final int TEXT_DIM     = 0xFF8A96A2;
    private static final int TEXT_FAINT   = 0xFF5A6672;
    private static final int HOVER        = 0x14FFFFFF;

    private static final int ROW_H = 22;
    private static final int PAD = 10;
    private static final int BOTTOM_H = 68;
    private static final int CRUMB_H = 14;

    /** How long the cursor must rest on a control before it names itself. */
    private static final long TOOLTIP_DELAY_MS = 450L;

    private static final long DEBOUNCE_MS = 400L;
    private static final int MIN_QUERY = 2;

    private static final int TAB_SONGS = 0, TAB_ARTISTS = 1, TAB_PLAYLISTS = 2,
                             TAB_LIBRARY = 3, TAB_QUEUE = 4, TAB_PUBLIC = 5,
                             TAB_UPLOAD = 6, TAB_DEVICES = 7;
    private static final String[] TAB_NAMES = { "Songs", "Artists", "Playlists",
                                                "Library", "Queue", "Public", "Upload", "Devices" };

    /**
     * Where the sound comes from. Fixed for a wall jukebox; for a JBL it is the
     * player, refreshed every tick so the source walks with them.
     */
    private double bx, by, bz;

    /** The speaker this screen belongs to, or null when a block owns it. */
    private final String speakerId;

    private GuiTextField search;
    private int tab = TAB_SONGS;

    private List<Track> local = new ArrayList<Track>();
    private volatile List<Track> remote = new ArrayList<Track>();
    private List<Track> results = new ArrayList<Track>();

    /** What the visible list holds right now, whichever view is showing. */
    private List<Track> rows = new ArrayList<Track>();
    private List<String> textRows = new ArrayList<String>();

    private String artistFilter;
    private String openPlaylist;
    private boolean namingPlaylist;

    /** Shared playlists: the browse list, and which one is open. */
    private List<PublicPlaylists.Entry> publicRows = new ArrayList<PublicPlaylists.Entry>();
    private String openPublic;
    private PublicPlaylists.Entry menuPublic;
    private int checkX, checkY, checkW, checkH = 12;

    private float scroll, scrollTarget;
    private int selected = -1;
    private int left, top, panelW, panelH, listTop, listH, visibleRows;

    private String lastQuery = " ";
    private int lastIndexSize = -1, lastRemoteSize = -1;
    private long typedAt;
    private boolean dispatched = true;
    private String dispatchedQuery = "";
    private int caretTimer;

    private String toast;
    private long toastUntil;

    // Row action menu. It serves songs and playlists both; exactly one is set.
    private Track menuTrack;
    private String menuPlaylist;
    private int menuX, menuY, menuW;
    private List<String> menuItems = new ArrayList<String>();

    /** The "add to playlist" chooser: which track, and whether it is naming a new one. */
    private Track pendingTrack;
    private boolean modalNaming;
    private GuiTextField modalField;
    private int modalX, modalY, modalW, modalH;

    /** Hover timing, so labels appear on a rest rather than on every sweep. */
    private String hoverKey;
    private long hoverSince;
    private String tooltip;
    private int tooltipX, tooltipY;

    private int backX, backY, backW;

    /**
     * How far the jukebox carries, as a few named sizes rather than a second
     * slider. Range and volume are different questions -- one is how loud the box
     * is, the other is how much of the world it fills -- and mixing them into one
     * control is what makes people turn the music up to be heard further away.
     *
     * Each entry is the radius that stays at full volume, then the distance where
     * it has faded to nothing. The gap between them is where the sound becomes
     * directional, so the two move together.
     *
     * It stops at Block. Stadium and Festival belong to the tower speakers, which is
     * what makes building a pair of them worth doing -- a jukebox that carried a
     * third of a kilometre on its own left the towers with nothing to be for.
     */
    private static final String[] RANGE_NAMES = { "Booth", "Room", "Hall", "Block" };
    private static final float[] RANGE_FULL   = {   6f,     12f,    20f,    36f };
    private static final float[] RANGE_MAX    = {  40f,     70f,   120f,   200f };

    private GuiTextField codeField;
    private int codeX, codeY, codeW, connectX, connectW;

    private boolean rangeOpen;
    private int rangeX, rangeY, rangeW, rangeH = 14;

    private int volX, volY, volW, volH;
    private boolean draggingVolume;
    private int barX, barY, barW, barH;
    private boolean draggingProgress;
    private long dragPositionMs;

    private int[] tabX = new int[TAB_NAMES.length];
    private int[] tabW = new int[TAB_NAMES.length];
    private int tabY, tabH = 15;

    /** A screen for the jukebox block at these coordinates. */
    public GuiJukebox(double bx, double by, double bz) {
        this(bx, by, bz, null);
    }

    /** A screen for a portable speaker, which sounds from wherever its owner is. */
    public GuiJukebox(String speakerId) {
        this(0, 0, 0, speakerId);
    }

    private GuiJukebox(double bx, double by, double bz, String speakerId) {
        this.speakerId = speakerId;
        this.bx = bx; this.by = by; this.bz = bz;
        followPlayer();
    }

    @Override public boolean doesGuiPauseGame() { return false; }

    @Override
    public void initGui() {
        Keyboard.enableRepeatEvents(true);

        panelW = Math.min(width - 40, 460);
        panelH = Math.min(height - 40, 320);
        left = (width - panelW) / 2;
        top = (height - panelH) / 2;

        // Asked for on every open, not only when the Devices tab is: the list has to
        // be in hand before the first play, or the first track after opening the
        // screen comes out of the jukebox alone while the hall stays silent.
        Devices.refresh();

        codeField = new GuiTextField(fontRendererObj, 0, 0, 10, 12);
        codeField.setMaxStringLength(com.questforge.content.net.SpeakerCodec.MAX_CODE);
        codeField.setEnableBackgroundDrawing(false);

        search = new GuiTextField(fontRendererObj, left + PAD + 16, top + 26,
                                  panelW - PAD * 2 - 20, 14);
        search.setMaxStringLength(96);
        search.setFocused(true);

        tabY = top + 48;

        // The padding shrinks until the row fits rather than being fixed, because a
        // fixed one puts the last tab off the edge of the panel the moment either
        // the window is small or a tab is added -- and a tab you cannot click is
        // worse than a cramped one.
        int room = panelW - PAD * 2;
        int cushion = 14, gap = 4;
        while (cushion > 4 && tabsWidth(cushion, gap) > room) cushion -= 2;
        while (gap > 1 && tabsWidth(cushion, gap) > room) gap--;

        int x = left + PAD;
        for (int i = 0; i < TAB_NAMES.length; i++) {
            tabW[i] = fontRendererObj.getStringWidth(TAB_NAMES[i]) + cushion;
            tabX[i] = x;
            x += tabW[i] + gap;
        }

        // A breadcrumb strip sits between the tabs and the list, and only takes
        // space when there is somewhere to go back to.
        listTop = top + 70 + ((nested() || tab == TAB_UPLOAD || tab == TAB_DEVICES) ? CRUMB_H : 0);
        listH = panelH - BOTTOM_H - (listTop - top);
        visibleRows = Math.max(1, listH / ROW_H);

        modalField = new GuiTextField(fontRendererObj, 0, 0, 10, 14);
        modalField.setMaxStringLength(48);

        int rowY = top + panelH - 24;
        volH = 14;
        volY = rowY + 2;
        volW = 92;
        volX = left + panelW - PAD - volW;

        // Between the transport and the volume readout, where there is room and
        // where it is plainly not part of either.
        rangeW = 52;
        rangeY = volY;
        rangeX = left + PAD + 96;

        barX = left + PAD + 34;
        barY = top + panelH - 32;
        barH = 4;
        barW = Math.max(40, (left + panelW - PAD - 34) - barX);

        JukeboxSettings.load();
        MusicIndex.ensureBuilt();
        refilter();
    }


    /** How wide the whole tab row would be at a given cushion and gap. */
    private int tabsWidth(int cushion, int gap) {
        int total = gap * (TAB_NAMES.length - 1);
        for (int i = 0; i < TAB_NAMES.length; i++) {
            total += fontRendererObj.getStringWidth(TAB_NAMES[i]) + cushion;
        }
        return total;
    }

    @Override public void onGuiClosed() { Keyboard.enableRepeatEvents(false); }

    @Override
    public void updateScreen() {
        super.updateScreen();
        caretTimer++;
        followPlayer();
    }

    /**
     * Keeps a speaker's anchor on its owner.
     *
     * Every play call takes the position to sound from, so simply moving this is
     * enough to make a portable speaker follow the player -- with the anchor sitting
     * on the listener, the audio engine's own distance and panning maths resolve to
     * full volume and no direction, which is exactly what a speaker on your shoulder
     * should sound like.
     */
    private void followPlayer() {
        if (speakerId == null) return;
        net.minecraft.client.entity.EntityClientPlayerMP me =
                net.minecraft.client.Minecraft.getMinecraft().thePlayer;
        if (me == null) return;
        bx = me.posX; by = me.posY; bz = me.posZ;
    }

    // ------------------------------------------------------------------
    // Searching
    // ------------------------------------------------------------------

    private String query() { return search == null ? "" : search.getText().trim(); }

    private void refilter() {
        String q = query();
        local = MusicIndex.search(q);

        if (!q.equals(dispatchedQuery)) {
            remote = new ArrayList<Track>();
            dispatched = false;
            typedAt = System.currentTimeMillis();
        }
        lastQuery = search == null ? "" : search.getText();
        lastIndexSize = MusicIndex.all().size();
        lastRemoteSize = remote.size();
        rebuild();
    }

    /**
     * What the Songs and Artists tabs draw from.
     *
     * Catalog results only. Your own files used to be mixed in here, which meant a
     * search for a song you owned returned it twice -- once from disk, once from the
     * catalog -- with no way to tell which was which until you played it. They live
     * on the Upload tab now, where the folders they came from are also managed, so
     * "my music" and "everyone's music" are two places rather than one blended list.
     */
    private void rebuild() {
        results = remote;
        buildRows();
    }

    /** Fills the visible list for whichever view is showing. */
    private void buildRows() {
        rows = new ArrayList<Track>();
        textRows = new ArrayList<String>();
        publicRows = new ArrayList<PublicPlaylists.Entry>();

        if (tab == TAB_SONGS) {
            for (int i = 0; i < results.size(); i++) {
                Track t = results.get(i);
                if (artistFilter == null || artistFilter.equalsIgnoreCase(t.artist)) rows.add(t);
            }

        } else if (tab == TAB_ARTISTS) {
            LinkedHashSet<String> names = new LinkedHashSet<String>();
            for (int i = 0; i < results.size(); i++) {
                String a = results.get(i).artist;
                if (!a.isEmpty()) names.add(a);
            }
            textRows.addAll(names);

        } else if (tab == TAB_PLAYLISTS) {
            if (openPlaylist == null) {
                textRows.add("+  New playlist");
                textRows.addAll(Library.playlistNames());
            } else {
                rows.addAll(Library.playlist(openPlaylist));
            }

        } else if (tab == TAB_LIBRARY) {
            rows.addAll(Library.savedTracks());

        } else if (tab == TAB_QUEUE) {
            rows.addAll(Queue.items());

        } else if (tab == TAB_UPLOAD) {
            // Straight off the index, filtered by the same search box as everything
            // else, so one query works wherever you happen to be.
            rows.addAll(local);

        } else if (tab == TAB_PUBLIC) {
            if (openPublic == null) {
                publicRows = PublicCache.index();
            } else {
                // Null while the songs are still on their way from the server; the
                // empty message says so rather than claiming the playlist is empty.
                List<Track> shared = PublicCache.tracks(openPublic);
                if (shared != null) rows.addAll(shared);
            }
        }

        clampScroll();
    }

    private int rowCount() {
        if (tab == TAB_ARTISTS || isPlaylistIndex()) return textRows.size();
        if (isPublicIndex()) return publicRows.size();
        return rows.size();
    }

    private boolean isPlaylistIndex() { return tab == TAB_PLAYLISTS && openPlaylist == null; }

    private boolean isPublicIndex() { return tab == TAB_PUBLIC && openPublic == null; }

    /** True when the current tab has drilled into something worth backing out of. */
    /** The block this screen belongs to, for addressing its device list. */
    public int blockX() { return (int) Math.floor(bx); }
    public int blockY() { return (int) Math.floor(by); }
    public int blockZ() { return (int) Math.floor(bz); }

    private boolean nested() {
        if (tab == TAB_PLAYLISTS) return openPlaylist != null;
        if (tab == TAB_PUBLIC) return openPublic != null;
        if (tab == TAB_SONGS) return artistFilter != null;
        return false;
    }

    /** Where we are, for the breadcrumb to say. */
    private String crumb() {
        if (tab == TAB_PLAYLISTS && openPlaylist != null) return "Playlists  /  " + openPlaylist;
        if (tab == TAB_SONGS && artistFilter != null) return "Artists  /  " + artistFilter;
        if (tab == TAB_PUBLIC && openPublic != null) {
            PublicPlaylists.Entry e = PublicCache.byId(openPublic);
            return e == null ? "Public" : "Public  /  " + e.name + "  by " + e.owner;
        }
        return "";
    }

    /** Steps out one level. The breadcrumb and Escape share this. */
    private void goBack() {
        if (tab == TAB_PLAYLISTS && openPlaylist != null) {
            openPlaylist = null;
        } else if (tab == TAB_PUBLIC && openPublic != null) {
            openPublic = null;
        } else if (tab == TAB_SONGS && artistFilter != null) {
            // Back to the artist list, which is what the trail above the list says
            // is behind here. Dropping the filter but staying on Songs left the
            // player one tab away from where the breadcrumb had promised to return.
            artistFilter = null;
            tab = TAB_ARTISTS;
        }
        selected = -1;
        scroll = scrollTarget = 0;
        closeMenu();
        layoutList();
        buildRows();
    }

    /**
     * The list grows and shrinks as the breadcrumb comes and goes, so its geometry
     * is recomputed rather than fixed at open.
     */
    private void layoutList() {
        listTop = top + 70 + ((nested() || tab == TAB_UPLOAD || tab == TAB_DEVICES) ? CRUMB_H : 0);
        listH = panelH - BOTTOM_H - (listTop - top);
        visibleRows = Math.max(1, listH / ROW_H);
    }

    private void maybeDispatch() {
        if (dispatched) return;
        if (System.currentTimeMillis() - typedAt < DEBOUNCE_MS) return;

        final String q = query();
        dispatched = true;
        dispatchedQuery = q;

        if (q.length() < MIN_QUERY) {
            remote = new ArrayList<Track>();
            rebuild();
            return;
        }
        Catalog.search(q, new Catalog.Listener() {
            @Override public void onResults(List<Track> tracks, boolean done) {
                if (!q.equals(dispatchedQuery)) return;
                remote = tracks;
            }
        });
    }

    private void clampScroll() {
        int max = Math.max(0, rowCount() - visibleRows);
        if (scrollTarget > max) scrollTarget = max;
        if (scrollTarget < 0) scrollTarget = 0;
        if (scroll > max) scroll = max;
        if (scroll < 0) scroll = 0;
    }

    // ------------------------------------------------------------------
    // Input
    // ------------------------------------------------------------------

    @Override
    protected void keyTyped(char c, int key) {
        if (tab == TAB_DEVICES && codeField != null && codeField.isFocused()) {
            if (key == Keyboard.KEY_RETURN || key == Keyboard.KEY_NUMPADENTER) {
                connectPasted();
                return;
            }
            if (key == Keyboard.KEY_ESCAPE) { codeField.setFocused(false); return; }
            codeField.textboxKeyTyped(c, key);
            return;
        }

        // The chooser owns the keyboard while it is open.
        if (pendingTrack != null) {
            if (key == Keyboard.KEY_ESCAPE) {
                if (modalNaming) { modalNaming = false; modalField.setText(""); }
                else pendingTrack = null;
                return;
            }
            if (modalNaming) {
                if (key == Keyboard.KEY_RETURN) { commitNewPlaylist(); return; }
                modalField.textboxKeyTyped(c, key);
            }
            return;
        }

        if (menuOpen() && key == Keyboard.KEY_ESCAPE) { closeMenu(); return; }
        if (rangeOpen && key == Keyboard.KEY_ESCAPE) { rangeOpen = false; return; }

        if (key == Keyboard.KEY_ESCAPE) {
            if (namingPlaylist) { namingPlaylist = false; search.setText(""); refilter(); return; }
            if (nested()) { goBack(); return; }
            mc.displayGuiScreen(null);
            return;
        }

        if (key == Keyboard.KEY_BACK && search.getText().isEmpty() && nested()) {
            goBack();
            return;
        }

        if (key == Keyboard.KEY_TAB) {
            tab = (tab + 1) % TAB_NAMES.length;
            onTabChanged();
            return;
        }

        if (key == Keyboard.KEY_UP)    { move(-1); return; }
        if (key == Keyboard.KEY_DOWN)  { move(1); return; }
        if (key == Keyboard.KEY_PRIOR) { move(-visibleRows); return; }
        if (key == Keyboard.KEY_NEXT)  { move(visibleRows); return; }

        if (key == Keyboard.KEY_RETURN) {
            if (namingPlaylist) {
                if (Library.createPlaylist(query())) {
                    say("Created \"" + query() + "\"");
                    namingPlaylist = false;
                    search.setText("");
                    refilter();
                } else {
                    say("That name is taken");
                }
                return;
            }
            if (selected >= 0) activate(selected, isShiftKeyDown());
            return;
        }

        if (search.textboxKeyTyped(c, key)) {
            scroll = scrollTarget = 0;
            selected = -1;
            if (!namingPlaylist) refilter();
            return;
        }
        super.keyTyped(c, key);
    }

    private void move(int delta) {
        int count = rowCount();
        if (count == 0) return;
        selected = selected < 0 ? 0 : selected + delta;
        if (selected < 0) selected = 0;
        if (selected >= count) selected = count - 1;
        if (selected < scrollTarget) scrollTarget = selected;
        if (selected >= scrollTarget + visibleRows) scrollTarget = selected - visibleRows + 1;
        clampScroll();
    }

    private void onTabChanged() {
        selected = -1;
        scroll = scrollTarget = 0;
        closeMenu();
        pendingTrack = null;
        rangeOpen = false;
        // Leaving the naming prompt behind would strand the search box in a mode
        // with no visible way out -- which is one way tabs stopped responding.
        if (namingPlaylist) {
            namingPlaylist = false;
            search.setText("");
        }
        // Opening the Public tab is the only thing that asks the server for the
        // list, so a session that never browses costs nothing.
        if (tab == TAB_PUBLIC) PublicCache.refresh(false);
        if (tab == TAB_UPLOAD) MusicIndex.ensureBuilt();
        // The device list is the server's to know; opening the tab is what asks.
        if (tab == TAB_DEVICES) Devices.refresh();
        layoutList();
        buildRows();
    }

    @Override
    protected void mouseClicked(int mx, int my, int button) {
        // The Devices tab draws its own body, so it handles its own clicks -- but
        // only after the tab strip above it has had them.
        if (tab == TAB_DEVICES && my >= top + 70 && clickDevices(mx, my)) return;

        // Overlays get first refusal, innermost first.
        if (pendingTrack != null) {
            if (modalNaming) {
                modalField.mouseClicked(mx, my, button);
                if (mx >= modalX && mx <= modalX + modalW
                        && my >= modalY + modalH - 20 && my <= modalY + modalH - 4) {
                    commitNewPlaylist();
                }
                if (mx < modalX || mx > modalX + modalW
                        || my < modalY || my > modalY + modalH) pendingTrack = null;
                return;
            }
            int hit = chooserHit(mx, my);
            if (hit != -1) { choosePlaylist(hit); return; }
            if (mx < modalX || mx > modalX + modalW
                    || my < modalY || my > modalY + modalH) pendingTrack = null;
            return;
        }

        if (menuOpen()) {
            int hit = menuHit(mx, my);
            if (hit >= 0) { runMenu(hit); return; }
            closeMenu();
            return;
        }

        if (rangeOpen) {
            int hit = rangeMenuHit(mx, my);
            if (hit >= 0) { chooseRange(hit); return; }
            // Anything else dismisses it, including the chip that opened it.
            rangeOpen = false;
            if (overRange(mx, my)) return;
        }

        if (overAddFolder(mx, my)) {
            mc.displayGuiScreen(new GuiMusicFolders(this));
            return;
        }

        if (overRescan(mx, my)) {
            MusicIndex.rescan();
            return;
        }

        if (overClear(mx, my)) {
            search.setText("");
            search.setFocused(true);
            scroll = scrollTarget = 0;
            selected = -1;
            if (!namingPlaylist) refilter();
            return;
        }

        // The playing track's menu, so it does not have to be hunted down in a list.
        if (overNowDots(mx, my)) {
            Track now = nowTrack();
            if (now != null) { openMenu(now, mx, my, false); return; }
        }

        search.mouseClicked(mx, my, button);

        if (nested() && mx >= backX && mx <= backX + backW
                && my >= backY && my <= backY + CRUMB_H) {
            goBack();
            return;
        }

        if (showCheckbox() && mx >= checkX && mx <= checkX + checkW
                && my >= checkY && my <= checkY + checkH) {
            togglePublic();
            return;
        }

        for (int i = 0; i < TAB_NAMES.length; i++) {
            if (mx >= tabX[i] && mx <= tabX[i] + tabW[i] && my >= tabY && my <= tabY + tabH) {
                tab = i;
                onTabChanged();
                return;
            }
        }

        if (overRange(mx, my)) { rangeOpen = true; return; }
        if (overVolume(mx, my)) { draggingVolume = true; setVolumeFromMouse(mx); return; }
        if (overProgress(mx, my)) { draggingProgress = true; dragPositionMs = positionFromMouse(mx); return; }

        int transport = transportHit(mx, my);
        if (transport >= 0) { runTransport(transport); return; }

        // List
        if (my >= listTop && my < listTop + listH && mx >= left + PAD && mx <= left + panelW - PAD) {
            int index = (int) ((my - listTop + scroll * ROW_H) / ROW_H);
            if (index < 0 || index >= rowCount()) return;
            selected = index;

            // The action button sits at the right of a hovered row.
            boolean onDots = mx >= actionsX() && mx <= actionsX() + 12;
            if (onDots && !rows.isEmpty() && index < rows.size()) {
                openMenu(rows.get(index), mx, my);
                return;
            }
            // Row 0 of the playlist index is "New playlist", which has no menu.
            if (onDots && isPlaylistIndex() && index > 0 && index < textRows.size()) {
                openPlaylistMenu(textRows.get(index), mx, my);
                return;
            }
            if (onDots && isPublicIndex() && index < publicRows.size()) {
                openPublicMenu(publicRows.get(index), mx, my);
                return;
            }
            activate(index, isShiftKeyDown());
            return;
        }
    }

    /** Plays, opens or performs the default action for a row. */
    private void activate(int index, boolean queueInstead) {
        if (tab == TAB_ARTISTS) {
            if (index < textRows.size()) {
                artistFilter = textRows.get(index);
                tab = TAB_SONGS;
                onTabChanged();
            }
            return;
        }

        if (isPublicIndex()) {
            if (index < publicRows.size()) {
                openPublic = publicRows.get(index).id;
                selected = -1;
                scroll = scrollTarget = 0;
                layoutList();
                buildRows();
            }
            return;
        }

        if (isPlaylistIndex()) {
            if (index == 0) {
                namingPlaylist = true;
                search.setText("");
                search.setFocused(true);
                say("Type a name, press Enter");
            } else if (index - 1 < Library.playlistNames().size()) {
                openPlaylist = Library.playlistNames().get(index - 1);
                selected = -1;
                scroll = scrollTarget = 0;
                buildRows();
            }
            return;
        }

        if (index >= rows.size()) return;
        Track t = rows.get(index);

        if (queueInstead) {
            Queue.add(t);
            say("Queued " + t.title);
            return;
        }

        // One meaning for clicking a song, wherever it is clicked: play it now.
        // The queue keeps its shape either way -- picking a row out of the queue
        // starts there, picking one anywhere else slots into the same place -- and
        // the track that was playing is dropped, because it has been left behind.
        if (tab == TAB_QUEUE) Queue.playFromQueue(index, bx, by, bz);
        else Queue.playImmediately(t, bx, by, bz);

        say("Playing " + t.title);
        bind(t);
    }

    private void bind(Track t) {
        // A jukebox remembers what it was left playing so the block can start again
        // on its own. A speaker has no block to remember anything, and its queue is
        // already kept for it -- so there is nothing to send.
        if (speakerId != null) return;
        com.questforge.content.net.QFNetwork.toServer(
                new com.questforge.content.net.PacketBindTrack(
                        (int) Math.floor(bx), (int) Math.floor(by), (int) Math.floor(bz), t.key()));
    }

    @Override
    protected void mouseClickMove(int mx, int my, int button, long heldFor) {
        if (draggingVolume) setVolumeFromMouse(mx);
        else if (draggingProgress) dragPositionMs = positionFromMouse(mx);
        else super.mouseClickMove(mx, my, button, heldFor);
    }

    @Override
    protected void mouseMovedOrUp(int mx, int my, int state) {
        if (state != -1) {
            if (draggingVolume) { draggingVolume = false; JukeboxSettings.save(); }
            if (draggingProgress) { draggingProgress = false; Playback.seek(dragPositionMs); }
        }
        super.mouseMovedOrUp(mx, my, state);
    }

    @Override
    public void handleMouseInput() {
        super.handleMouseInput();
        int wheel = Mouse.getEventDWheel();
        if (wheel == 0) return;
        scrollTarget += wheel > 0 ? -3 : 3;
        clampScroll();
    }

    // ------------------------------------------------------------------
    // Row action menu
    // ------------------------------------------------------------------

    private boolean menuOpen() {
        return menuTrack != null || menuPlaylist != null || menuPublic != null;
    }

    private void closeMenu() { menuTrack = null; menuPlaylist = null; menuPublic = null; }

    private void openMenu(Track t, int mx, int my) { openMenu(t, mx, my, true); }

    /**
     * @param inList whether this was opened from a row. The "remove from" entries
     *               act on the selected row, so they belong only to a menu that a
     *               row opened -- from the now-playing bar they would remove
     *               whatever happened to be highlighted somewhere else.
     */
    private void openMenu(Track t, int mx, int my, boolean inList) {
        closeMenu();
        menuTrack = t;
        menuItems = new ArrayList<String>();
        menuItems.add("Play next");
        menuItems.add("Add to queue");
        menuItems.add(Library.isSaved(t) ? "Remove from Library" : "Save to Library");
        // One entry that opens a chooser, rather than a menu that grows a line per
        // playlist and eventually runs off the screen.
        menuItems.add("Add to playlist...");
        if (inList && tab == TAB_QUEUE) menuItems.add("Remove from queue");
        if (inList && openPlaylist != null) menuItems.add("Remove from playlist");
        placeMenu(mx, my);
    }

    /**
     * The same menu, for a playlist rather than a song. A playlist that can be made
     * but never removed is a one-way door, and the row it sits on is the only place
     * anyone would look for the way out of it.
     */
    private void openPlaylistMenu(String name, int mx, int my) {
        closeMenu();
        menuPlaylist = name;
        menuItems = new ArrayList<String>();
        menuItems.add("Play all");
        menuItems.add("Add to queue");
        menuItems.add("Delete playlist");
        placeMenu(mx, my);
    }

    private void placeMenu(int mx, int my) {
        menuW = 100;
        for (int i = 0; i < menuItems.size(); i++) {
            menuW = Math.max(menuW, fontRendererObj.getStringWidth(menuItems.get(i)) + 16);
        }
        menuX = Math.min(mx, left + panelW - menuW - 4);
        menuY = Math.min(my, top + panelH - menuItems.size() * 12 - 4);
    }

    private int menuHit(int mx, int my) {
        if (mx < menuX || mx > menuX + menuW) return -1;
        int index = (my - menuY) / 12;
        return index >= 0 && index < menuItems.size() ? index : -1;
    }

    private void runMenu(int index) {
        if (index < 0 || index >= menuItems.size()) { closeMenu(); return; }

        Track t = menuTrack;
        String list = menuPlaylist;
        PublicPlaylists.Entry shared = menuPublic;
        String action = menuItems.get(index);
        closeMenu();

        if (shared != null) { runPublicMenu(shared, action); return; }
        if (list != null) { runPlaylistMenu(list, action); return; }
        if (t == null) return;

        if (action.equals("Play next")) {
            Queue.playNext(t);
            say("Playing next: " + t.title);
        } else if (action.equals("Add to queue")) {
            Queue.add(t);
            say("Queued " + t.title);
        } else if (action.startsWith("Save to") || action.startsWith("Remove from Library")) {
            say(Library.toggleSave(t) ? "Saved " + t.title : "Removed " + t.title);
            if (tab == TAB_LIBRARY) buildRows();
        } else if (action.equals("Remove from queue")) {
            Queue.remove(selected);
            buildRows();
        } else if (action.equals("Remove from playlist")) {
            Library.removeFromPlaylist(openPlaylist, selected);
            buildRows();
        } else if (action.equals("Add to playlist...")) {
            openPlaylistChooser(t);
        }
    }

    // ------------------------------------------------------------------
    // Shared playlists
    // ------------------------------------------------------------------

    private String myId() {
        try {
            return mc.thePlayer.getUniqueID().toString();
        } catch (Throwable t) {
            return "";
        }
    }

    private String myName() {
        try {
            return mc.thePlayer.getCommandSenderName();
        } catch (Throwable t) {
            return "";
        }
    }

    /**
     * Whether an entry is this player's own. The id is the real test; the name is a
     * fallback, because a client's idea of its own UUID is not guaranteed to match
     * the one the server filed the playlist under, and being wrong about that would
     * silently hide someone's own Stop sharing.
     */
    private boolean isMine(PublicPlaylists.Entry e) {
        if (e == null) return false;
        return myId().equals(e.ownerId) || (!myName().isEmpty() && myName().equals(e.owner));
    }

    /** Whether one of this player's own playlists is currently shared. */
    private boolean isShared(String name) {
        List<PublicPlaylists.Entry> index = PublicCache.index();
        for (int i = 0; i < index.size(); i++) {
            PublicPlaylists.Entry e = index.get(i);
            if (e.name.equals(name) && isMine(e)) return true;
        }
        return false;
    }

    private void togglePublic() {
        if (openPlaylist == null) return;

        boolean shared = isShared(openPlaylist);
        List<Track> tracks = Library.playlist(openPlaylist);
        if (!shared && tracks.isEmpty()) {
            say("Put a song in it before sharing it");
            return;
        }
        if (!shared && tracks.size() > PublicPlaylists.MAX_TRACKS) {
            say("Sharing the first " + PublicPlaylists.MAX_TRACKS + " songs");
        }

        com.questforge.content.net.QFNetwork.toServer(
                new com.questforge.content.net.PacketPublishPlaylist(
                        !shared, openPlaylist, tracks));
        // The server answers with a fresh index, which is what actually moves the
        // tick -- so the box follows what was really shared, not what was asked.
        PublicCache.refresh(true);
    }

    private void openPublicMenu(PublicPlaylists.Entry e, int mx, int my) {
        closeMenu();
        menuPublic = e;
        menuItems = new ArrayList<String>();
        menuItems.add("View songs");
        menuItems.add("Play all");
        menuItems.add("Add to queue");
        menuItems.add("Save to my playlists");
        if (isMine(e)) menuItems.add("Stop sharing");
        placeMenu(mx, my);
    }

    private void runPublicMenu(PublicPlaylists.Entry e, String action) {
        if (action.equals("View songs")) {
            openPublic = e.id;
            selected = -1;
            scroll = scrollTarget = 0;
            layoutList();
            buildRows();
            return;
        }
        if (action.equals("Stop sharing")) {
            com.questforge.content.net.QFNetwork.toServer(
                    new com.questforge.content.net.PacketPublishPlaylist(
                            false, e.name, null));
            PublicCache.refresh(true);
            return;
        }

        List<Track> shared = PublicCache.tracks(e.id);
        if (shared == null) {
            // The request has just gone out; one more click will have it.
            say("Fetching \"" + e.name + "\"...");
            return;
        }
        if (shared.isEmpty()) { say("\"" + e.name + "\" is no longer shared"); return; }

        if (action.equals("Play all")) {
            Queue.replaceWith(shared, bx, by, bz);
            bind(shared.get(0));
            say("Playing " + e.name);

        } else if (action.equals("Add to queue")) {
            Queue.addAll(shared);
            say("Queued " + shared.size() + " from " + e.name);

        } else if (action.equals("Save to my playlists")) {
            String name = e.name;
            // Someone else's "Bangers" must not merge into yours.
            if (Library.hasPlaylist(name)) name = e.name + " (" + e.owner + ")";
            if (!Library.createPlaylist(name)) { say("You already saved that one"); return; }

            for (int i = 0; i < shared.size(); i++) Library.addToPlaylist(name, shared.get(i));
            say("Saved as \"" + name + "\"");
        }
    }

    private void runPlaylistMenu(String name, String action) {
        List<Track> tracks = Library.playlist(name);

        if (action.equals("Play all")) {
            if (tracks.isEmpty()) { say("\"" + name + "\" is empty"); return; }
            Queue.replaceWith(tracks, bx, by, bz);
            bind(tracks.get(0));
            say("Playing " + name);

        } else if (action.equals("Add to queue")) {
            if (tracks.isEmpty()) { say("\"" + name + "\" is empty"); return; }
            Queue.addAll(tracks);
            say("Queued " + tracks.size() + " from " + name);

        } else if (action.equals("Delete playlist")) {
            Library.deletePlaylist(name);
            if (name.equals(openPlaylist)) openPlaylist = null;
            say("Deleted \"" + name + "\"");
            selected = -1;
            layoutList();
            buildRows();
        }
    }

    // ------------------------------------------------------------------
    // Add-to-playlist chooser
    // ------------------------------------------------------------------

    private void openPlaylistChooser(Track t) {
        pendingTrack = t;
        modalNaming = false;
        modalField.setText("");

        modalW = 190;
        int lines = Library.playlistNames().size();
        modalH = 30 + Math.max(1, lines) * 14 + 24;
        modalX = left + (panelW - modalW) / 2;
        modalY = top + (panelH - modalH) / 2;

        modalField.xPosition = modalX + 10;
        modalField.yPosition = modalY + modalH - 40;
        modalField.width = modalW - 20;
    }

    /** Rows in the chooser: one per playlist, then the create action. */
    private int chooserHit(int mx, int my) {
        if (mx < modalX || mx > modalX + modalW) return -1;
        int listY = modalY + 26;
        int index = (my - listY) / 14;
        int count = Library.playlistNames().size();
        if (index >= 0 && index < count) return index;
        // The create button sits on the bottom edge, whatever the list length.
        if (my >= modalY + modalH - 20 && my <= modalY + modalH - 4) return -2;
        return -1;
    }

    private void choosePlaylist(int hit) {
        Track t = pendingTrack;
        if (t == null) return;

        if (hit == -2) {
            // Creating from here adds the song straight away, which is the only
            // reason someone would be making a playlist at this moment.
            modalNaming = true;
            modalField.setFocused(true);
            return;
        }
        List<String> names = Library.playlistNames();
        if (hit < 0 || hit >= names.size()) return;

        String name = names.get(hit);
        say(Library.addToPlaylist(name, t) ? "Added to " + name : "Already in " + name);
        pendingTrack = null;
    }

    private void commitNewPlaylist() {
        String name = modalField.getText().trim();
        if (name.isEmpty()) return;

        if (!Library.createPlaylist(name)) {
            say("That name is taken");
            return;
        }
        Library.addToPlaylist(name, pendingTrack);
        say("Created " + name + " and added the song");
        pendingTrack = null;
        modalNaming = false;
        modalField.setText("");
        if (tab == TAB_PLAYLISTS) buildRows();
    }

    private void say(String message) {
        toast = message;
        toastUntil = System.currentTimeMillis() + 2500L;
    }

    // ------------------------------------------------------------------
    // Transport
    // ------------------------------------------------------------------

    private int transportX() { return left + PAD; }
    private int transportY() { return top + panelH - 22; }

    /** Buttons are laid out left to right at a fixed pitch; index or -1. */
    private int transportHit(int mx, int my) {
        int y = transportY();
        if (my < y || my > y + 14) return -1;
        int x = transportX();
        for (int i = 0; i < 5; i++) {
            if (mx >= x + i * 18 && mx <= x + i * 18 + 15) return i;
        }
        return -1;
    }

    private void runTransport(int index) {
        if (index == 0) {
            if (!Queue.previous(bx, by, bz)) Playback.replay();
        } else if (index == 1) {
            // A track put down when its jukebox was broken resumes here, at this
            // one, from the second it stopped.
            if (!DirectAudio.isActive() && Playback.hasSuspended()) {
                Playback.resumeSuspended(bx, by, bz);
            } else {
                Playback.togglePause();
            }
        } else if (index == 2) {
            if (!Queue.next(bx, by, bz)) say("Nothing queued");
        } else if (index == 3) {
            Playback.setLooping(!Playback.isLooping());
            JukeboxSettings.save();
        } else if (index == 4) {
            // Clear the song, not the queue: stop what is sounding and take it out
            // of the list, leaving everything lined up behind it alone.
            boolean was = DirectAudio.isActive() || Playback.loading() != null
                       || Playback.hasSuspended();
            Playback.stop();
            Playback.forget();
            Queue.dropCurrent();
            if (was) say("Cleared");
        }
    }

    private boolean overVolume(int mx, int my) {
        return mx >= volX && mx <= volX + volW && my >= volY && my <= volY + volH;
    }

    // ------------------------------------------------------------------
    // Range
    // ------------------------------------------------------------------

    private static final int RANGE_MENU_W = 112;

    private boolean overRange(int mx, int my) {
        return mx >= rangeX && mx <= rangeX + rangeW && my >= rangeY && my <= rangeY + rangeH;
    }

    private int rangeMenuY() { return rangeY - (RANGE_NAMES.length * 12 + 4) - 3; }

    /** Which preset the saved range matches, or -1 if it was set by hand. */
    private int currentRange() {
        float full = DirectAudio.getRefDistance();
        for (int i = 0; i < RANGE_FULL.length; i++) {
            if (Math.abs(RANGE_FULL[i] - full) < 0.5f) return i;
        }
        return -1;
    }

    private String rangeLabel() {
        int i = currentRange();
        return i < 0 ? Math.round(DirectAudio.getRefDistance()) + "b" : RANGE_NAMES[i];
    }

    private int rangeMenuHit(int mx, int my) {
        if (!rangeOpen || mx < rangeX || mx > rangeX + RANGE_MENU_W) return -1;
        int index = (my - rangeMenuY() - 2) / 12;
        return index >= 0 && index < RANGE_NAMES.length ? index : -1;
    }

    private void chooseRange(int index) {
        rangeOpen = false;
        if (index < 0 || index >= RANGE_NAMES.length) return;

        DirectAudio.setRange(RANGE_FULL[index], RANGE_MAX[index]);
        JukeboxSettings.save();
        say(RANGE_NAMES[index] + "  ·  full volume within "
                + (int) RANGE_FULL[index] + " blocks");
    }

    private void drawRange(int mx, int my) {
        boolean hot = rangeOpen || overRange(mx, my);

        drawRect(rangeX, rangeY, rangeX + rangeW, rangeY + rangeH, FIELD);
        outline(rangeX, rangeY, rangeX + rangeW, rangeY + rangeH,
                hot ? 0xFF3E4952 : RULE);

        String label = rangeLabel();
        fontRendererObj.drawString(label, rangeX + 6, rangeY + 3, hot ? TEXT : TEXT_DIM);

        // A caret, so it reads as something that opens rather than a readout.
        int cx = rangeX + rangeW - 9, cy = rangeY + 5;
        for (int i = 0; i < 3; i++) {
            drawRect(cx - 2 + i, cy + i, cx + 3 - i, cy + i + 1, hot ? TEXT : TEXT_DIM);
        }

        if (hot && !rangeOpen) hover("range", "Range", mx + 8, my - 16);
    }

    private void drawRangeMenu(int mx, int my) {
        if (!rangeOpen) return;

        int h = RANGE_NAMES.length * 12 + 4;
        int y = rangeMenuY();

        drawRect(rangeX, y, rangeX + RANGE_MENU_W, y + h, 0xF81A2027);
        outline(rangeX, y, rangeX + RANGE_MENU_W, y + h, 0xFF3E4952);

        int current = currentRange();
        for (int i = 0; i < RANGE_NAMES.length; i++) {
            int iy = y + 2 + i * 12;
            boolean hover = mx >= rangeX && mx <= rangeX + RANGE_MENU_W
                         && my >= iy && my < iy + 12;
            if (hover) drawRect(rangeX + 1, iy, rangeX + RANGE_MENU_W - 1, iy + 12, ACCENT_SOFT);

            fontRendererObj.drawString(RANGE_NAMES[i], rangeX + 6, iy + 2,
                    i == current ? ACCENT : hover ? TEXT : TEXT_DIM);

            String blocks = (int) RANGE_FULL[i] + " blocks";
            fontRendererObj.drawString(blocks,
                    rangeX + RANGE_MENU_W - 6 - fontRendererObj.getStringWidth(blocks),
                    iy + 2, i == current ? ACCENT : TEXT_FAINT);
        }
    }

    private void setVolumeFromMouse(int mx) {
        float fraction = (mx - (volX + 2)) / (float) Math.max(1, volW - 4);
        DirectAudio.setVolume(fraction * DirectAudio.MAX_VOLUME);
    }

    private boolean overProgress(int mx, int my) {
        return Playback.durationMs() > 0
                && mx >= barX - 3 && mx <= barX + barW + 3
                && my >= barY - 5 && my <= barY + barH + 5;
    }

    private long positionFromMouse(int mx) {
        float fraction = (mx - barX) / (float) Math.max(1, barW);
        if (fraction < 0f) fraction = 0f;
        if (fraction > 1f) fraction = 1f;
        return (long) (Playback.durationMs() * fraction);
    }

    private int actionsX() { return left + panelW - PAD - 14; }

    /** Whatever the player is listening to, playing, loading, or set down. */
    private Track nowTrack() {
        Track t = Playback.playing();
        if (t == null) t = Playback.loading();
        if (t == null) t = Playback.suspendedTrack();
        return t;
    }

    private int nowDotsX = -1, nowDotsY;

    private boolean overNowDots(int mx, int my) {
        return nowDotsX >= 0 && mx >= nowDotsX && mx <= nowDotsX + 12
                             && my >= nowDotsY - 2 && my <= nowDotsY + 12;
    }

    /** Geometry of the search box's clear button, set while it is drawn. */
    private int clearX = -1, clearY, clearSize = 12;

    /** The Upload tab's toolbar, laid out while it is drawn. */
    private int addFolderX = -1, addFolderY, addFolderW;
    private int rescanX = -1, rescanY, rescanW;


    private boolean overClear(int mx, int my) {
        return clearX >= 0 && mx >= clearX && mx <= clearX + clearSize
                           && my >= clearY && my <= clearY + clearSize;
    }

    // ------------------------------------------------------------------
    // Drawing
    // ------------------------------------------------------------------

    @Override
    public void drawScreen(int mx, int my, float partial) {
        maybeDispatch();

        if (tab == TAB_SONGS || tab == TAB_ARTISTS || tab == TAB_UPLOAD) {
            // The index publishes in batches while it scans, so the Upload tab fills
            // in as the worker finds files rather than staying empty until the whole
            // library has been read. On a big folder that is the difference between
            // "working" and "frozen".
            if (MusicIndex.all().size() != lastIndexSize
                    || !search.getText().equals(lastQuery)) {
                if (!namingPlaylist) refilter();
            } else if (remote.size() != lastRemoteSize) {
                lastRemoteSize = remote.size();
                rebuild();
            }
        }

        // Shared playlists arrive in packets rather than being read, so the list is
        // rebuilt when what the server sent stops matching what is on screen.
        if (tab == TAB_PUBLIC) {
            if (openPublic == null) {
                PublicCache.refresh(false);
                if (publicRows.size() != PublicCache.index().size()) buildRows();
            } else if (rows.isEmpty()) {
                List<Track> shared = PublicCache.tracks(openPublic);
                if (shared != null && !shared.isEmpty()) buildRows();
            }
        }

        // Eased scrolling. The list settles toward its target instead of stepping,
        // which is most of what makes a list feel smooth rather than mechanical.
        scroll += (scrollTarget - scroll) * 0.35f;
        if (Math.abs(scrollTarget - scroll) < 0.01f) scroll = scrollTarget;

        drawDefaultBackground();
        drawRect(left, top, left + panelW, top + panelH, PANEL);
        outline(left, top, left + panelW, top + panelH, PANEL_EDGE);

        tooltip = null;
        layoutList();

        drawHeader();
        drawSearchBox(mx, my);
        drawTabs(mx, my);
        drawCrumb(mx, my);
        drawUploadBar(mx, my);
        drawDeviceBar(mx, my);
        drawList(mx, my);
        drawNowPlaying(mx, my);
        drawMenu(mx, my);
        drawRangeMenu(mx, my);
        drawChooser(mx, my);
        drawToast();
        drawTooltip();

        super.drawScreen(mx, my, partial);
    }

    private void drawHeader() {
        fontRendererObj.drawString(EnumChatFormatting.BOLD + "JUKEBOX", left + PAD, top + 10, TEXT);

        String status;
        int color = TEXT_FAINT;
        if (Catalog.isSearching())        { status = "searching"; color = ACCENT; }
        else if (MusicIndex.isIndexing()) { status = MusicIndex.status(); color = ACCENT; }
        else if (Catalog.error() != null) { status = "offline"; color = 0xFFD08A8A; }
        else if (DirectAudio.isActive())  { status = playingStatus(); color = ACCENT; }
        else                              { status = rowCount() + " results"; }

        int w = fontRendererObj.getStringWidth(status);
        fontRendererObj.drawString(status, left + panelW - PAD - w, top + 10, color);
        // A small lamp, so the state reads at a glance without being read.
        drawRect(left + panelW - PAD - w - 8, top + 12, left + panelW - PAD - w - 4, top + 16, color);
    }

    /**
     * What the header says while music is running.
     *
     * It used to say LINKED, which meant only that an OpenAL source existed -- true
     * of every second of playback and therefore telling nobody anything. Where the
     * sound is actually coming out is a fact a player cannot otherwise see, and the
     * one they want when a speaker across the base has gone quiet.
     */
    private String playingStatus() {
        int on = 0;
        for (SpeakerRegistry.Entry e : Devices.list()) if (e.enabled) on++;
        if (on == 0) return "PLAYING";
        return on == 1 ? "PLAYING + 1 SPEAKER" : "PLAYING + " + on + " SPEAKERS";
    }

    private void drawSearchBox(int mx, int my) {
        int x = left + PAD, y = top + 24, w = panelW - PAD * 2, h = 18;
        drawRect(x, y, x + w, y + h, FIELD);
        outline(x, y, x + w, y + h, search.isFocused() ? 0xFF3E4952 : RULE);

        // Magnifier, drawn small: a ring and a handle.
        int gx = x + 6, gy = y + 6;
        outline(gx, gy, gx + 6, gy + 6, TEXT_DIM);
        drawRect(gx + 6, gy + 6, gx + 8, gy + 8, TEXT_DIM);

        String text = search.getText();
        int textX = x + 16, textY = y + 5;

        // The clear button, only while there is something to clear.
        if (text.isEmpty()) {
            clearX = -1;
        } else {
            clearX = x + w - clearSize - 4;
            clearY = y + (h - clearSize) / 2;

            boolean on = overClear(mx, my);
            if (on) drawRect(clearX, clearY, clearX + clearSize, clearY + clearSize, HOVER);

            // A cross, drawn as two diagonals a pixel at a time.
            int cx = clearX + clearSize / 2, cy = clearY + clearSize / 2;
            for (int i = -3; i <= 3; i++) {
                drawRect(cx + i, cy + i, cx + i + 1, cy + i + 1, on ? TEXT : TEXT_DIM);
                drawRect(cx + i, cy - i, cx + i + 1, cy - i + 1, on ? TEXT : TEXT_DIM);
            }
            if (on) hover("clear", "Clear", mx + 8, my + 14);
        }

        int room = clearX >= 0 ? clearX - textX - 6 : w - 24;
        if (text.isEmpty()) {
            fontRendererObj.drawString(namingPlaylist
                    ? "name the playlist, then press Enter"
                    : "search for a song, artist or album", textX, textY, TEXT_FAINT);
        } else {
            fontRendererObj.drawString(trim(text, room), textX, textY, TEXT);
        }

        if (search.isFocused() && (caretTimer / 6) % 2 == 0) {
            int cursor = Math.max(0, Math.min(search.getCursorPosition(), text.length()));
            int caretX = textX + fontRendererObj.getStringWidth(text.substring(0, cursor));
            drawRect(caretX, y + 4, caretX + 1, y + h - 4, ACCENT);
        }
    }

    private void drawTabs(int mx, int my) {
        for (int i = 0; i < TAB_NAMES.length; i++) {
            boolean active = i == tab;
            boolean hover = mx >= tabX[i] && mx <= tabX[i] + tabW[i]
                         && my >= tabY && my <= tabY + tabH;

            if (active) drawRect(tabX[i], tabY, tabX[i] + tabW[i], tabY + tabH, ACCENT_SOFT);
            else if (hover) drawRect(tabX[i], tabY, tabX[i] + tabW[i], tabY + tabH, HOVER);

            String name = TAB_NAMES[i];
            int tx = tabX[i] + (tabW[i] - fontRendererObj.getStringWidth(name)) / 2;
            fontRendererObj.drawString(name, tx, tabY + 4, active ? ACCENT : TEXT_DIM);

            // The active tab is underlined rather than boxed, which keeps the row
            // quiet while still being unambiguous.
            if (active) drawRect(tabX[i], tabY + tabH - 1, tabX[i] + tabW[i], tabY + tabH, ACCENT);
        }
        drawRect(left + PAD, tabY + tabH, left + panelW - PAD, tabY + tabH + 1, RULE);
    }

    /**
     * The breadcrumb. Appears only when there is somewhere to go back to, so the
     * list keeps its full height the rest of the time.
     */
    private void drawCrumb(int mx, int my) {
        if (!nested()) return;

        backY = top + 70;
        backX = left + PAD;
        backW = 18 + fontRendererObj.getStringWidth("Back") + 4;

        boolean hover = mx >= backX && mx <= backX + backW
                     && my >= backY && my <= backY + CRUMB_H;
        if (hover) drawRect(backX, backY, backX + backW, backY + CRUMB_H, HOVER);

        int color = hover ? ACCENT : TEXT_DIM;

        // A left-pointing arrow: the head is a point at the left that widens to the
        // right, with a tail running out behind it. Built the other way round it
        // read as the play triangle sitting two rows below.
        int ax = backX + 4, ay = backY + CRUMB_H / 2;
        for (int i = 0; i < 4; i++) drawRect(ax + i, ay - i, ax + i + 1, ay + i + 1, color);
        drawRect(ax + 3, ay - 1, ax + 10, ay + 1, color);

        fontRendererObj.drawString("Back", backX + 18, backY + 3, color);

        int crumbX = backX + backW + 8;
        drawRect(crumbX - 5, backY + 2, crumbX - 4, backY + CRUMB_H - 2, RULE);

        int crumbRoom = left + panelW - PAD - crumbX;
        if (showCheckbox()) crumbRoom -= checkW + 8;
        fontRendererObj.drawString(trim(crumb(), crumbRoom), crumbX, backY + 3, TEXT_FAINT);

        if (showCheckbox()) drawPublicCheck(mx, my);
    }

    private boolean showCheckbox() { return tab == TAB_PLAYLISTS && openPlaylist != null; }

    /**
     * The share switch, on the row above the songs it would share.
     *
     * Deliberately loud when it is on: this is the one control in the screen whose
     * effect is visible to other people, and a quiet tick in a corner is not enough
     * warning that a playlist has left your machine.
     */
    private void drawPublicCheck(int mx, int my) {
        boolean shared = isShared(openPlaylist);

        String label = "PUBLIC";
        checkW = 16 + fontRendererObj.getStringWidth(label) + 6;
        checkX = left + panelW - PAD - checkW;
        checkY = backY + 1;

        boolean hover = mx >= checkX && mx <= checkX + checkW
                     && my >= checkY && my <= checkY + checkH;

        if (shared) drawRect(checkX, checkY, checkX + checkW, checkY + checkH, ACCENT_SOFT);
        else if (hover) drawRect(checkX, checkY, checkX + checkW, checkY + checkH, HOVER);
        outline(checkX, checkY, checkX + checkW, checkY + checkH,
                shared ? ACCENT : hover ? 0xFF3E4952 : RULE);

        // The box itself, with a drawn tick rather than a character the font may
        // not have.
        int bx0 = checkX + 4, by0 = checkY + 3;
        outline(bx0, by0, bx0 + 7, by0 + 7, shared ? ACCENT : TEXT_DIM);
        if (shared) {
            drawRect(bx0 + 1, by0 + 3, bx0 + 3, by0 + 5, ACCENT);
            drawRect(bx0 + 3, by0 + 2, bx0 + 6, by0 + 4, ACCENT);
        }

        fontRendererObj.drawString(label, checkX + 16, checkY + 2,
                                   shared ? ACCENT : hover ? TEXT : TEXT_DIM);

        if (hover) hover("public", shared ? "Shared" : "Share", mx + 8, my - 16);
    }


    // ------------------------------------------------------------------
    // Devices
    // ------------------------------------------------------------------

    /** How tall one device row is. Taller than a track row: it carries two lines. */
    private static final int DEVICE_H = 22;

    /**
     * The paste box, in the band the breadcrumb would otherwise use.
     *
     * A speaker is connected by carrying its code here, so the one control the tab
     * cannot do without is somewhere to put that code -- and it sits above the list
     * because that is the order the job happens in.
     */
    private void drawDeviceBar(int mx, int my) {
        if (tab != TAB_DEVICES) return;

        int y = top + 70;
        int h = CRUMB_H;

        connectW = 54;
        connectX = left + panelW - PAD - connectW;
        codeX = left + PAD;
        codeY = y;
        codeW = connectX - 6 - codeX;

        codeField.xPosition = codeX + 4;
        codeField.yPosition = y + 3;
        codeField.width = codeW - 8;

        drawRect(codeX, y, codeX + codeW, y + h - 2, FIELD);
        outline(codeX, y, codeX + codeW, y + h - 2,
                codeField.isFocused() ? 0xFF3E4952 : RULE);
        if (codeField.getText().isEmpty() && !codeField.isFocused()) {
            fontRendererObj.drawString("Paste a speaker code", codeX + 5, y + 3, TEXT_FAINT);
        }
        codeField.drawTextBox();

        boolean over = mx >= connectX && mx <= connectX + connectW
                    && my >= y && my <= y + h - 2;
        drawRect(connectX, y, connectX + connectW, y + h - 2, over ? 0xFF2A343D : FIELD);
        outline(connectX, y, connectX + connectW, y + h - 2, over ? ACCENT : RULE);
        int cw = fontRendererObj.getStringWidth("Connect");
        fontRendererObj.drawString("Connect", connectX + (connectW - cw) / 2, y + 3,
                                   over ? ACCENT : TEXT_DIM);
    }

    /**
     * The owner and everything paired to it, each with a switch.
     *
     * The owner is listed first and looks like any other row on purpose: a jukebox
     * is one speaker among several once it has company, and being able to silence it
     * while the hall keeps playing is the whole reason the list has switches at all.
     */
    private void drawDevices(int mx, int my) {
        java.util.List<SpeakerRegistry.Entry> list = Devices.list();

        int y = listTop + 2;
        deviceRowY = y;

        drawDeviceRow(mx, my, y, ownerLabel(), "This one", Devices.ownerEnabled(), "", 0);
        y += DEVICE_H;

        for (SpeakerRegistry.Entry e : list) {
            String detail = e.code + "   " + Devices.RANGE_NAMES[
                    e.range < 0 ? 0 : e.range >= Devices.RANGE_NAMES.length
                            ? Devices.RANGE_NAMES.length - 1 : e.range]
                    + "   " + distanceTo(e);
            drawDeviceRow(mx, my, y, e.name, detail, e.enabled, e.code, 1);
            y += DEVICE_H;
            if (y > listTop + listH - DEVICE_H) break;
        }

        if (list.isEmpty()) {
            fontRendererObj.drawString(
                    "No speakers connected. Place one, right-click it, and copy its code.",
                    left + PAD + 2, y + 6, TEXT_FAINT);
        }

        String problem = Devices.problem();
        if (!problem.isEmpty()) {
            fontRendererObj.drawString(problem, left + PAD + 2,
                                       listTop + listH - 10, 0xFFD08A8A);
        }
    }

    private int deviceRowY;

    private void drawDeviceRow(int mx, int my, int y, String name, String detail,
                               boolean on, String code, int kind) {
        int x0 = left + PAD, x1 = left + panelW - PAD;
        boolean hover = mx >= x0 && mx <= x1 && my >= y && my < y + DEVICE_H;
        if (hover) drawRect(x0, y, x1, y + DEVICE_H, HOVER);

        // The switch. A filled lamp reads as on from further away than a tick does.
        int sw = x0 + 4;
        drawRect(sw, y + 6, sw + 10, y + 14, on ? ACCENT : RULE);
        outline(sw, y + 6, sw + 10, y + 14, on ? ACCENT : 0xFF3E4952);

        fontRendererObj.drawString(trim(name, 150), x0 + 20, y + 3, on ? TEXT : TEXT_DIM);
        fontRendererObj.drawString(trim(detail, panelW - PAD * 2 - 40), x0 + 20, y + 12,
                                   TEXT_FAINT);

        if (kind == 1) {
            int dx = x1 - 14;
            boolean overX = mx >= dx && mx <= dx + 10 && my >= y + 6 && my <= y + 16;
            fontRendererObj.drawString("x", dx + 3, y + 7, overX ? 0xFFD08A8A : TEXT_FAINT);

            // The speaker's own screen, without walking to it. Drawn as three dots
            // rather than written as one, because the vertical ellipsis is not in
            // the game's font and would come out as a blank.
            int ox = deviceMenuX(y);
            boolean overMenu = overDeviceMenu(mx, my, y);
            int dot = overMenu ? TEXT : TEXT_FAINT;
            for (int i = 0; i < 3; i++) {
                drawRect(ox + 4, y + 6 + i * 4, ox + 6, y + 8 + i * 4, dot);
            }
        }
    }

    private int deviceMenuX(int rowY) { return left + panelW - PAD - 30; }

    private boolean overDeviceMenu(int mx, int my, int rowY) {
        int ox = deviceMenuX(rowY);
        return mx >= ox && mx <= ox + 10 && my >= rowY + 5 && my <= rowY + 17;
    }

    private String ownerLabel() {
        return Speakers.isSpeaker() ? "This JBL" : "This jukebox";
    }

    /** How far the speaker is, so an unheard one can be told from a broken one. */
    private String distanceTo(SpeakerRegistry.Entry e) {
        net.minecraft.client.Minecraft game = net.minecraft.client.Minecraft.getMinecraft();
        if (game.thePlayer == null) return "";
        double dx = e.x + 0.5 - game.thePlayer.posX;
        double dy = e.y + 1.0 - game.thePlayer.posY;
        double dz = e.z + 0.5 - game.thePlayer.posZ;
        return Math.round(Math.sqrt(dx * dx + dy * dy + dz * dz)) + "m";
    }

    /** Returns true when the click belonged to the Devices tab. */
    private boolean clickDevices(int mx, int my) {
        if (tab != TAB_DEVICES) return false;

        codeField.mouseClicked(mx, my, 0);

        int barY = top + 70;
        if (mx >= connectX && mx <= connectX + connectW
                && my >= barY && my <= barY + CRUMB_H - 2) {
            connectPasted();
            return true;
        }
        if (my < listTop) return true;

        int index = (my - deviceRowY) / DEVICE_H;
        if (index < 0) return true;

        if (index == 0) {
            Devices.act(com.questforge.content.net.PacketDeviceAction.TOGGLE, "");
            return true;
        }
        java.util.List<SpeakerRegistry.Entry> list = Devices.list();
        int at = index - 1;
        if (at >= list.size()) return true;
        SpeakerRegistry.Entry e = list.get(at);

        int rowY = deviceRowY + index * DEVICE_H;
        int dx = left + panelW - PAD - 14;
        if (mx >= dx && mx <= dx + 10 && my >= rowY + 6 && my <= rowY + 16) {
            Devices.act(com.questforge.content.net.PacketDeviceAction.UNPAIR, e.code);
        } else if (overDeviceMenu(mx, my, rowY)) {
            // The server answers this one with the speaker's screen, and only for a
            // speaker actually paired to us -- so nothing here needs to decide
            // whether it is allowed.
            Devices.act(com.questforge.content.net.PacketDeviceAction.OPEN, e.code);
        } else {
            Devices.act(com.questforge.content.net.PacketDeviceAction.TOGGLE, e.code);
        }
        return true;
    }

    private void connectPasted() {
        String code = SpeakerRegistry.normalise(codeField.getText());
        if (code.isEmpty()) { say("Paste a speaker code first"); return; }
        Devices.act(com.questforge.content.net.PacketDeviceAction.PAIR, code);
        codeField.setText("");
    }

    private void drawList(int mx, int my) {
        if (tab == TAB_DEVICES) { drawDevices(mx, my); return; }

        int count = rowCount();

        if (count == 0) {
            fontRendererObj.drawString(emptyMessage(), left + PAD + 2, listTop + 8, TEXT_FAINT);
            return;
        }

        // Clipped, so a partly scrolled row cannot bleed into the tabs or the
        // player below it.
        beginClip(left + PAD, listTop, panelW - PAD * 2, listH);

        int first = (int) Math.floor(scroll);
        int offset = (int) ((scroll - first) * ROW_H);

        for (int i = 0; i <= visibleRows; i++) {
            int index = first + i;
            if (index < 0 || index >= count) continue;

            int ry = listTop + i * ROW_H - offset;
            boolean hover = mx >= left + PAD && mx <= left + panelW - PAD
                         && my >= ry && my < ry + ROW_H && my >= listTop && my < listTop + listH;

            if (index == selected) drawRect(left + PAD, ry, left + panelW - PAD, ry + ROW_H, ACCENT_SOFT);
            else if (hover)        drawRect(left + PAD, ry, left + panelW - PAD, ry + ROW_H, HOVER);

            if (isPublicIndex()) {
                if (index < publicRows.size()) {
                    drawPublicRow(publicRows.get(index), index, ry, hover, mx, my);
                }
            } else if (index < rows.size() && !isPlaylistIndex() && tab != TAB_ARTISTS) {
                drawTrackRow(rows.get(index), index, ry, hover, mx, my);
            } else if (index < textRows.size()) {
                // Playlists carry a count and their own menu; artists are just names.
                String tally = null;
                boolean dots = false;
                if (isPlaylistIndex() && index > 0) {
                    int n = Library.playlist(textRows.get(index)).size();
                    tally = n + (n == 1 ? " song" : " songs");
                    // Sharing is visible from the index too, not only from inside.
                    if (isShared(textRows.get(index))) tally = "public  ·  " + tally;
                    dots = hover;
                    if (hover && overDots(mx)) hover("plmenu" + index, "More", mx + 8, my - 16);
                }
                drawTextRow(textRows.get(index), ry, dots, tally);
            }
        }
        endClip();

        drawScrollbar(count);
    }

    private void drawTrackRow(Track t, int index, int ry, boolean hover, int mx, int my) {
        int artSize = 16;
        int ax = left + PAD + 3;
        AlbumArt.draw(t, ax, ry + 2, artSize);

        boolean isCurrent = t.equals(Playback.playing());
        int textX = ax + artSize + 6;
        int rightEdge = hover ? actionsX() - 6 : left + panelW - PAD - 4;

        String duration = t.durationText();
        int durW = duration.isEmpty() ? 0 : fontRendererObj.getStringWidth(duration);
        if (durW > 0) {
            fontRendererObj.drawString(duration, rightEdge - durW, ry + 6,
                                       isCurrent ? ACCENT : TEXT_FAINT);
        }

        int titleW = (rightEdge - durW - 8) - textX;
        fontRendererObj.drawString(trim(t.title, titleW), textX, ry + 2,
                                   isCurrent ? ACCENT : TEXT);

        // Second line carries artist and album, the way every music player does,
        // so the title above it can stay a title.
        String sub = t.artistText();
        if (!t.album.isEmpty()) sub = sub + "  ·  " + t.album;
        fontRendererObj.drawString(trim(sub, titleW), textX, ry + 11, TEXT_DIM);

        if (Library.isSaved(t)) {
            drawDiamond(textX - 5, ry + 4, ACCENT);
        }

        if (hover) {
            drawActionDots(actionsX(), ry + ROW_H / 2 - 4);
            // Only over the dots themselves, and beside the cursor. Anchored to the
            // row instead, it announced itself for the whole width of a row it did
            // not describe, and drew above the list where nothing had been clicked.
            if (overDots(mx)) hover("dots" + index, "More", mx + 8, my - 16);
        }
    }

    /**
     * A shared playlist in the browse list: what it is called, who shared it, and
     * how big it is. The publisher is on the row rather than hidden in a menu,
     * because whose playlist it is is most of what makes one worth opening.
     */
    private void drawPublicRow(PublicPlaylists.Entry e, int index, int ry,
                               boolean hover, int mx, int my) {
        int textX = left + PAD + 8;
        int rightEdge = hover ? actionsX() - 6 : left + panelW - PAD - 4;

        String size = e.count + (e.count == 1 ? " song" : " songs");
        int sizeW = fontRendererObj.getStringWidth(size);
        fontRendererObj.drawString(size, rightEdge - sizeW, ry + 6, TEXT_FAINT);

        boolean mine = isMine(e);
        int width = (rightEdge - sizeW - 8) - textX;

        fontRendererObj.drawString(trim(e.name, width), textX, ry + 2, mine ? ACCENT : TEXT);
        fontRendererObj.drawString(trim("shared by " + e.owner, width),
                                   textX, ry + 11, TEXT_DIM);

        if (hover) {
            drawActionDots(actionsX(), ry + ROW_H / 2 - 4);
            if (overDots(mx)) hover("pub" + index, "More", mx + 8, my - 16);
        }
    }

    /** True when the cursor is on a row's action button. */
    private boolean overDots(int mx) {
        return mx >= actionsX() && mx <= actionsX() + 12;
    }

    private void drawTextRow(String label, int ry, boolean showDots, String right) {
        int textX = left + PAD + 8;
        int rightEdge = showDots ? actionsX() - 6 : left + panelW - PAD - 4;

        if (right != null) {
            int w = fontRendererObj.getStringWidth(right);
            fontRendererObj.drawString(right, rightEdge - w, ry + 7, TEXT_FAINT);
            rightEdge -= w + 8;
        }
        fontRendererObj.drawString(trim(label, rightEdge - textX), textX, ry + 7, TEXT);

        if (showDots) drawActionDots(actionsX(), ry + ROW_H / 2 - 4);
    }

    /** Three dots: the universal "more actions", and cheap to draw. */
    private void drawActionDots(int x, int y) {
        for (int i = 0; i < 3; i++) {
            drawRect(x + 4, y + i * 4, x + 6, y + i * 4 + 2, TEXT_DIM);
        }
    }

    private void drawDiamond(int x, int y, int color) {
        for (int i = 0; i < 3; i++) {
            drawRect(x - i, y + 2 - i, x + i + 1, y + 3 - i, color);
            drawRect(x - i, y + 2 + i, x + i + 1, y + 3 + i, color);
        }
    }

    /**
     * The Upload tab's toolbar: where the music is coming from, and how far along.
     *
     * It sits in the band the breadcrumb uses, because the two are never on screen
     * together, and a tab that manages something should say so at the top rather
     * than hiding it behind a menu.
     *
     * The progress bar is the reactive half. Indexing a real music folder takes long
     * enough that with no feedback the tab looks broken -- so while a scan runs this
     * fills and counts, and the list underneath grows as files are found.
     */
    private void drawUploadBar(int mx, int my) {
        if (tab != TAB_UPLOAD) return;

        int y = top + 70;
        int h = CRUMB_H;

        String label = "+  Add folder";
        addFolderW = fontRendererObj.getStringWidth(label) + 12;
        addFolderX = left + PAD;
        addFolderY = y;

        boolean over = overAddFolder(mx, my);
        drawRect(addFolderX, y, addFolderX + addFolderW, y + h - 2, over ? 0xFF2A343D : FIELD);
        outline(addFolderX, y, addFolderX + addFolderW, y + h - 2, over ? ACCENT : RULE);
        fontRendererObj.drawString(label, addFolderX + 6, y + 3, over ? ACCENT : TEXT_DIM);

        int textX = addFolderX + addFolderW + 10;
        int right = left + panelW - PAD;

        if (MusicIndex.isIndexing()) {
            int total = Math.max(1, MusicIndex.total());
            int done = Math.min(MusicIndex.scanned(), total);

            String counting = MusicIndex.total() == 0
                    ? "looking for files"
                    : "reading tags  " + done + " / " + total;
            fontRendererObj.drawString(counting, textX, y + 3, ACCENT);

            int barX = textX + fontRendererObj.getStringWidth(counting) + 8;
            if (barX + 30 < right) {
                drawRect(barX, y + 5, right, y + 8, RULE);
                // Zero width would read as stuck rather than as just started.
                int filled = Math.max(2, (right - barX) * done / total);
                drawRect(barX, y + 5, barX + filled, y + 8, ACCENT);
            }
            rescanX = -1;
            return;
        }

        int folders = MusicFolders.extras().size() + 1;
        int tracks = MusicIndex.all().size();
        String summary = folders + (folders == 1 ? " folder" : " folders")
                + "  -  " + tracks + (tracks == 1 ? " track" : " tracks");
        fontRendererObj.drawString(summary, textX, y + 3, TEXT_FAINT);

        String rescan = "Rescan";
        rescanW = fontRendererObj.getStringWidth(rescan);
        rescanX = right - rescanW;
        rescanY = y;
        fontRendererObj.drawString(rescan, rescanX, y + 3,
                                   overRescan(mx, my) ? ACCENT : TEXT_FAINT);
    }

    private boolean overAddFolder(int mx, int my) {
        return tab == TAB_UPLOAD && addFolderX >= 0
            && mx >= addFolderX && mx <= addFolderX + addFolderW
            && my >= addFolderY && my <= addFolderY + CRUMB_H - 2;
    }

    private boolean overRescan(int mx, int my) {
        return tab == TAB_UPLOAD && rescanX >= 0 && !MusicIndex.isIndexing()
            && mx >= rescanX && mx <= rescanX + rescanW
            && my >= rescanY && my <= rescanY + CRUMB_H - 2;
    }

    private void drawScrollbar(int count) {
        if (count <= visibleRows) return;
        int trackX = left + panelW - PAD + 2;
        int barHeight = Math.max(12, listH * visibleRows / count);
        int max = count - visibleRows;
        int y = listTop + (int) ((listH - barHeight) * (scroll / Math.max(1, max)));

        drawRect(trackX, listTop, trackX + 2, listTop + listH, 0x18FFFFFF);
        drawRect(trackX, y, trackX + 2, y + barHeight, 0x66FFFFFF);
    }

    private String emptyMessage() {
        if (tab == TAB_QUEUE) return "The queue is empty. Use the dots on any song.";
        if (tab == TAB_LIBRARY) return "Nothing saved yet.";
        if (tab == TAB_UPLOAD) {
            if (MusicIndex.isIndexing()) return "Reading your music...";
            // The two reasons this list is empty are completely different problems,
            // and telling someone to add a folder when they have four is useless.
            if (MusicIndex.all().isEmpty()) {
                return "No music yet. Add a folder, or drop files in .minecraft/jukebox.";
            }
            return "No tracks of yours match that.";
        }
        if (tab == TAB_PLAYLISTS) {
            return openPlaylist == null
                    ? "No playlists yet."
                    : "\"" + openPlaylist + "\" is empty. Add songs with the dots on any row.";
        }
        if (tab == TAB_ARTISTS) return "Search first, then browse by artist.";
        if (tab == TAB_PUBLIC) {
            if (openPublic != null) {
                return PublicCache.tracks(openPublic) == null
                        ? "Fetching the songs..."
                        : "That playlist is not shared any more.";
            }
            if (!PublicCache.ready()) return "Asking the server...";
            return "Nobody has shared a playlist yet. Open one of yours and tick PUBLIC.";
        }
        if (Catalog.isSearching() || !dispatched) return "Searching...";
        if (query().length() < MIN_QUERY) return "Type to search millions of tracks";
        if (Catalog.error() != null) return "Could not reach the catalogs: " + Catalog.error();
        return "Nothing found for that search";
    }

    // ------------------------------------------------------------------
    // Player
    // ------------------------------------------------------------------

    private void drawNowPlaying(int mx, int my) {
        int y0 = top + panelH - BOTTOM_H;
        drawRect(left + PAD, y0, left + panelW - PAD, y0 + 1, RULE);

        Track t = nowTrack();
        if (t != null) AlbumArt.draw(t, left + PAD, y0 + 6, 24);

        int textX = left + PAD + 30;
        // The radius sits next to the distance so the two can be read against each
        // other: how far away you are, and how far away it stops being full.
        int full = Math.round(DirectAudio.getRefDistance());
        String label;
        if (speakerId != null) {
            // Distance and radius are meaningless for something you are carrying.
            label = "NOW PLAYING  ·  ON YOU";
        } else if (t != null && DirectAudio.isActive()) {
            int distance = (int) Math.round(Math.sqrt(
                    mc.thePlayer.getDistanceSq(bx, by, bz)));
            label = "NOW PLAYING  ·  " + distance + " BLOCKS AWAY  ·  FULL WITHIN " + full;
        } else {
            label = "NOW PLAYING  ·  FULL WITHIN " + full + " BLOCKS";
        }
        fontRendererObj.drawString(label, textX, y0 + 6, TEXT_FAINT);

        String now = Playback.status();
        boolean busy = Playback.loading() != null;
        fontRendererObj.drawString(
                trim(now.isEmpty() ? "nothing playing" : now, panelW - 76),
                textX, y0 + 17,
                busy ? 0xFFD8C89B : Playback.error() != null ? 0xFFD08A8A
                     : DirectAudio.isActive() ? ACCENT : TEXT_FAINT);

        // The playing track's own actions, without having to find it in a list.
        if (t != null) {
            nowDotsX = left + panelW - PAD - 14;
            nowDotsY = y0 + 12;
            boolean on = overNowDots(mx, my);
            drawActionDots(nowDotsX, nowDotsY);
            if (on) hover("nowdots", "More", mx + 8, my - 16);
        } else {
            nowDotsX = -1;
        }

        drawProgress(mx, my);
        drawTransport(mx, my);
        drawRange(mx, my);
        drawVolume(mx, my);
    }

    private void drawProgress(int mx, int my) {
        long duration = Playback.durationMs();
        boolean seekable = duration > 0;
        long position = draggingProgress ? dragPositionMs : Playback.positionMs();
        if (seekable && position > duration) position = duration;

        boolean hot = draggingProgress || overProgress(mx, my);
        drawRect(barX, barY, barX + barW, barY + barH, 0xFF1D2429);

        if (seekable) {
            int fill = (int) (barW * (position / (double) duration));
            if (fill > 0) drawRect(barX, barY, barX + fill, barY + barH, hot ? ACCENT : 0xFFB07F38);
            if (hot) drawRect(barX + fill - 1, barY - 2, barX + fill + 2, barY + barH + 2, TEXT);
        }

        fontRendererObj.drawString(seekable ? time(position) : "--:--",
                left + PAD, barY - 2, TEXT_FAINT);
        String total = seekable ? time(duration) : "live";
        fontRendererObj.drawString(total,
                left + panelW - PAD - fontRendererObj.getStringWidth(total), barY - 2, TEXT_FAINT);
    }

    private static final String[] TRANSPORT_LABELS =
            { "Previous", "Play", "Next", "Loop", "Clear Song" };

    /** Transport icons, drawn as shapes: the font has no glyphs for these. */
    private void drawTransport(int mx, int my) {
        int x = transportX(), y = transportY();
        int hovered = transportHit(mx, my);

        for (int i = 0; i < 5; i++) {
            int bx0 = x + i * 18;
            boolean on = i == 3 && Playback.isLooping();
            int color = on ? ACCENT : (hovered == i ? TEXT : TEXT_DIM);

            if (hovered == i) {
                drawRect(bx0 - 1, y - 1, bx0 + 16, y + 15, HOVER);
                String label = i == 1 && !DirectAudio.isPaused() && DirectAudio.isActive()
                        ? "Pause" : TRANSPORT_LABELS[i];
                hover("transport" + i, label, bx0, y - 14);
            }

            int cx = bx0 + 7, cy = y + 7;
            if (i == 0) {                                  // previous
                drawRect(cx - 5, cy - 5, cx - 3, cy + 5, color);
                triangle(cx + 4, cy, -1, color);

            } else if (i == 1) {                           // play / pause
                if (DirectAudio.isPaused() || !DirectAudio.isActive()) {
                    triangle(cx - 4, cy, 1, color);
                } else {
                    drawRect(cx - 4, cy - 5, cx - 1, cy + 5, color);
                    drawRect(cx + 1, cy - 5, cx + 4, cy + 5, color);
                }

            } else if (i == 2) {                           // next
                triangle(cx - 4, cy, 1, color);
                drawRect(cx + 3, cy - 5, cx + 5, cy + 5, color);

            } else if (i == 3) {
                // Repeat: a closed loop with an arrowhead, so it reads as "goes
                // round again" rather than the plain rectangle it used to be.
                drawRect(cx - 5, cy - 4, cx + 3, cy - 3, color);   // top run
                drawRect(cx - 3, cy + 3, cx + 5, cy + 4, color);   // bottom run
                drawRect(cx + 4, cy - 4, cx + 5, cy + 1, color);   // right turn
                drawRect(cx - 5, cy - 1, cx - 4, cy + 4, color);   // left turn
                for (int k = 0; k < 3; k++) {                      // arrowhead
                    drawRect(cx - 5 - k + 2, cy - 6 + k, cx - 2 + k, cy - 5 + k, color);
                }
                if (on) drawRect(cx - 1, cy - 1, cx + 1, cy + 1, ACCENT);

            } else {
                // Stop: a hollow square. Solid read as a blob next to the loop;
                // an outline is unmistakably a stop and matches the icon weight
                // of everything beside it.
                outline(cx - 5, cy - 5, cx + 5, cy + 5, color);
                drawRect(cx - 3, cy - 3, cx + 3, cy + 3, color);
            }
        }
    }

    /**
     * Registers a label for whatever the cursor is resting on. Held for a moment
     * before it shows, so sweeping across the controls stays quiet.
     */
    private void hover(String key, String label, int x, int y) {
        if (!key.equals(hoverKey)) {
            hoverKey = key;
            hoverSince = System.currentTimeMillis();
            return;
        }
        if (System.currentTimeMillis() - hoverSince < TOOLTIP_DELAY_MS) return;
        tooltip = label;
        tooltipX = x;
        tooltipY = y;
    }

    private void drawTooltip() {
        if (tooltip == null) return;
        int w = fontRendererObj.getStringWidth(tooltip) + 10;
        int x = Math.max(left + 2, Math.min(tooltipX, left + panelW - w - 2));
        int y = Math.max(top + 2, Math.min(tooltipY, top + panelH - 15));

        drawRect(x, y, x + w, y + 13, 0xF01A2027);
        outline(x, y, x + w, y + 13, 0xFF3E4952);
        fontRendererObj.drawString(tooltip, x + 5, y + 3, TEXT);
    }

    /** A solid triangle pointing right (dir 1) or left (dir -1), apex at x. */
    private void triangle(int x, int cy, int dir, int color) {
        for (int i = 0; i < 5; i++) {
            int half = 5 - i;
            int px = x + dir * i;
            drawRect(Math.min(px, px + 1), cy - half, Math.max(px, px + 1), cy + half, color);
        }
    }

    private void drawVolume(int mx, int my) {
        float v = DirectAudio.getVolume();
        boolean hot = draggingVolume || overVolume(mx, my);
        int track = volW - 4;

        drawRect(volX, volY, volX + volW, volY + volH, FIELD);
        outline(volX, volY, volX + volW, volY + volH, hot ? 0xFF3E4952 : RULE);

        int unityX = volX + 2 + (int) (track / DirectAudio.MAX_VOLUME);
        int fillW = (int) (track * (v / DirectAudio.MAX_VOLUME));
        int fillEnd = volX + 2 + fillW;

        if (fillW > 0) {
            drawRect(volX + 2, volY + 2, Math.min(fillEnd, unityX), volY + volH - 2, 0xFF3D6350);
            // Past unity the signal is amplified rather than turned up, so it is
            // marked as a different thing, not just more of the same.
            if (fillEnd > unityX) drawRect(unityX, volY + 2, fillEnd, volY + volH - 2, 0xFF9A6A34);
        }
        drawRect(unityX, volY + 2, unityX + 1, volY + volH - 2, 0x44FFFFFF);

        String label = Math.round(v * 100) + "%";
        fontRendererObj.drawString(label,
                volX - 4 - fontRendererObj.getStringWidth(label), volY + 3, TEXT_FAINT);
    }

    // ------------------------------------------------------------------
    // Overlays
    // ------------------------------------------------------------------

    private void drawMenu(int mx, int my) {
        if (!menuOpen()) return;
        int h = menuItems.size() * 12 + 4;

        drawRect(menuX, menuY, menuX + menuW, menuY + h, 0xF81A2027);
        outline(menuX, menuY, menuX + menuW, menuY + h, 0xFF3E4952);

        int hit = menuHit(mx, my);
        for (int i = 0; i < menuItems.size(); i++) {
            int iy = menuY + 2 + i * 12;
            if (i == hit) drawRect(menuX + 1, iy, menuX + menuW - 1, iy + 12, ACCENT_SOFT);

            // Deleting a playlist throws songs away; it should not look like the
            // entries above it, which are all reversible.
            boolean destructive = menuItems.get(i).startsWith("Delete");
            int color = destructive ? (i == hit ? 0xFFE08A8A : 0xFFB87878)
                                    : (i == hit ? ACCENT : TEXT);
            fontRendererObj.drawString(menuItems.get(i), menuX + 6, iy + 2, color);
        }
    }

    /**
     * The add-to-playlist chooser.
     *
     * Its own surface rather than a longer dropdown, because picking a playlist is
     * a decision about the song, and creating one mid-decision should not mean
     * abandoning it -- the create button here adds the song the moment the
     * playlist exists.
     */
    private void drawChooser(int mx, int my) {
        if (pendingTrack == null) return;

        // Dim what is behind it, so the choice is clearly the only live thing.
        drawRect(left, top, left + panelW, top + panelH, 0x99000000);

        drawRect(modalX, modalY, modalX + modalW, modalY + modalH, 0xFA141A20);
        outline(modalX, modalY, modalX + modalW, modalY + modalH, 0xFF3E4952);

        fontRendererObj.drawString("Add to playlist", modalX + 10, modalY + 8, TEXT);
        fontRendererObj.drawString(trim(pendingTrack.title, modalW - 20),
                                   modalX + 10, modalY + 18, TEXT_FAINT);

        int listY = modalY + 32;
        if (modalNaming) {
            fontRendererObj.drawString("New playlist name", modalX + 10, listY, TEXT_DIM);

            int fy = listY + 12;
            drawRect(modalX + 10, fy, modalX + modalW - 10, fy + 16, FIELD);
            outline(modalX + 10, fy, modalX + modalW - 10, fy + 16, 0xFF3E4952);

            String text = modalField.getText();
            fontRendererObj.drawString(trim(text, modalW - 28), modalX + 15, fy + 4, TEXT);
            if ((caretTimer / 6) % 2 == 0) {
                int caretX = modalX + 15 + fontRendererObj.getStringWidth(text);
                drawRect(caretX, fy + 3, caretX + 1, fy + 13, ACCENT);
            }
        } else {
            List<String> names = Library.playlistNames();
            if (names.isEmpty()) {
                fontRendererObj.drawString("No playlists yet", modalX + 10, listY + 4, TEXT_FAINT);
            }
            for (int i = 0; i < names.size(); i++) {
                int iy = listY - 6 + i * 14;
                boolean hover = mx >= modalX && mx <= modalX + modalW
                             && my >= iy && my < iy + 14;
                if (hover) drawRect(modalX + 4, iy, modalX + modalW - 4, iy + 14, ACCENT_SOFT);

                fontRendererObj.drawString(trim(names.get(i), modalW - 60),
                                           modalX + 12, iy + 3, hover ? ACCENT : TEXT);
                String n = Library.playlist(names.get(i)).size() + "";
                fontRendererObj.drawString(n,
                        modalX + modalW - 14 - fontRendererObj.getStringWidth(n), iy + 3, TEXT_FAINT);
            }
        }

        // Create button, pinned to the bottom edge.
        int by0 = modalY + modalH - 20;
        boolean hoverCreate = mx >= modalX + 10 && mx <= modalX + modalW - 10
                           && my >= by0 && my <= by0 + 16;
        drawRect(modalX + 10, by0, modalX + modalW - 10, by0 + 16,
                 hoverCreate ? 0xFF2A3A32 : 0xFF1D2429);
        outline(modalX + 10, by0, modalX + modalW - 10, by0 + 16,
                hoverCreate ? ACCENT : RULE);

        String action = modalNaming ? "Create and add" : "+  New playlist";
        fontRendererObj.drawString(action,
                modalX + (modalW - fontRendererObj.getStringWidth(action)) / 2, by0 + 4,
                hoverCreate ? ACCENT : TEXT_DIM);
    }

    private void drawToast() {
        if (toast == null || System.currentTimeMillis() > toastUntil) return;
        int w = fontRendererObj.getStringWidth(toast) + 16;
        int x = left + (panelW - w) / 2;
        int y = top + panelH - BOTTOM_H - 18;

        drawRect(x, y, x + w, y + 14, 0xE81A2027);
        outline(x, y, x + w, y + 14, 0xFF3E4952);
        fontRendererObj.drawString(toast, x + 8, y + 3, ACCENT);
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /** Scissor test, in real pixels: the GUI is drawn at a scaled resolution. */
    private void beginClip(int x, int y, int w, int h) {
        ScaledResolution sr = new ScaledResolution(mc, mc.displayWidth, mc.displayHeight);
        int factor = sr.getScaleFactor();
        GL11.glEnable(GL11.GL_SCISSOR_TEST);
        GL11.glScissor(x * factor, (sr.getScaledHeight() - (y + h)) * factor,
                       w * factor, h * factor);
    }

    private void endClip() { GL11.glDisable(GL11.GL_SCISSOR_TEST); }

    private void outline(int x1, int y1, int x2, int y2, int c) {
        drawRect(x1, y1, x2, y1 + 1, c);
        drawRect(x1, y2 - 1, x2, y2, c);
        drawRect(x1, y1, x1 + 1, y2, c);
        drawRect(x2 - 1, y1, x2, y2, c);
    }

    private static String time(long ms) {
        if (ms < 0) ms = 0;
        long total = ms / 1000L;
        long h = total / 3600, m = (total % 3600) / 60, s = total % 60;
        if (h > 0) return h + ":" + String.format("%02d:%02d", m, s);
        return m + ":" + String.format("%02d", s);
    }

    private String trim(String s, int maxPx) {
        if (s == null) return "";
        if (maxPx <= 0) return "";
        if (fontRendererObj.getStringWidth(s) <= maxPx) return s;
        while (s.length() > 1 && fontRendererObj.getStringWidth(s + "...") > maxPx) {
            s = s.substring(0, s.length() - 1);
        }
        return s + "...";
    }
}
