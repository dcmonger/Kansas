/**
 * The client provides an eventually-consistent view of the game state.
 * Synchronization works as follows. When the user moves a card, a "move"
 * message is sent to the server. This "move" is immediately applied locally.
 * The server then relays the move to all clients in a globally consistent order
 * relative to other moves.
 *
 * Clients, upon receiving an "update" message, will update the local state of
 * the card mentioned in the update. Once all clients have received the update,
 * all the client states will be in sync.
 *
 * The client can also talk to all other clients by using a "broadcast" message,
 * which again will be received by other clients in a globally consistent order.
 */


// Default settings for websocket connection.
var kWSPort = 8080
var hostname = window.location.hostname || "localhost"
var gameid = "testgame1";
var uuid = "p_" + Math.random().toString().substring(5);
var user = window.location.hash || "#alice";
var ws = null;
document.title = user + '@' + gameid;

// Configuration constants for grid spacing and logging.
var kGridSpacing = 35;
var loggingEnabled = false;

// Tracks local state of the hand and zIndex of the topmost card.
var handCache = [];
var localMaxZ = 200;

// Minimum zIndexes for various states.
var kHandZIndex = 4000000;
var kDraggingZIndex = 4500000;
var kPhantomZIndex = 5500000;

// The URL prefix from which card images are downloaded from.
var resourcePrefix = '';

// Tracks the dragging card, phantom, and card shown in hover menu.
var draggingCard = null;
var hoverCardId = null;
var lastPhantomLocation = 0;
var startPhantomLocation = 0;
var phantomHideQueued = {};

// Tracks mouseup/down state for correct event handling.
var disableArenaEvents = false;
var dragging = false;

// Workaround for https://github.com/benbarnett/jQuery-Animate-Enhanced/issues/97
var XXX_jitter = 1;

// Set to kAnimationLength once initial load has completed.
var animationLength = 0;
var kAnimationLength = 500;


// Geometry of cards.
var kCardWidth = 140;
var kCardHeight = 200;
var kHoverCardRatio = 4;
var kHoverTapRatio = kHoverCardRatio * 0.875;

/**
 * When cards are stacked on each other we want to provide a 3d-illusion.
 * heightOf() returns the proper x, y offset for cards in the stack.
 */
function heightOf(stackHeight) {
    if (stackHeight >= kHandZIndex) {
        return 0;
    }
    var kStackDelta = 2;
    var kMaxVisibleStackHeight = 9;
    if (stackHeight > kMaxVisibleStackHeight) {
        stackHeight = kMaxVisibleStackHeight;
    }
    return stackHeight * kStackDelta;
}

/* Returns absolute url of a resource. */
function toResource(url) {
    if (url && url.toString().substring(0,5) == "http:") {
        return url;
    } else {
        return resourcePrefix + url;
    }
}

/* Highlights hand to receive drops. */
function activateHand() {
    deactivateQueued = false;
    $("#hand").addClass("active");
}

/* Removes highlight from hand. */
function deactivateHand() {
    deactivateQueued = false;
    $("#hand").removeClass("active");
}

/* Removes highlight from hand after a while. */
var deactivateQueued = false;
function deferDeactivateHand() {
    deactivateQueued = true;
    setTimeout(_reallyDeactivateHand, 1000);
}

function _reallyDeactivateHand() {
    if (deactivateQueued) {
        $("#hand").removeClass("active");
        deactivateQueued = false;
    }
}

/* Shows the "Loading..." spinner. */
var spinnerShowQueued = false;
function showSpinner() {
    if (!spinnerShowQueued) {
        spinnerShowQueued = true;
        setTimeout(_reallyShowSpinner, 500);
    }
}

function _reallyShowSpinner() {
    if (spinnerShowQueued) {
        $("#spinner").show();
        spinnerShowQueued = false;
    }
}

/* Hides the "Loading..." spinner. */
function hideSpinner() {
    spinnerShowQueued = false;
    $("#spinner").hide();
}

/**
 * Utility that removes an element from an array.
 * Returns if the element was present in the array.
 */
function removeFromArray(arr, item) {
    var idx = $.inArray(item, arr);
    if (idx >= 0) {
        arr.splice(idx, 1);
        log("Removing item " + item + " from array.");
        return true;
    } else {
        log("Item " + item + " not in array.");
        return false;
    }
}

/* Logs a message to the debug console */
function log(msg) {
    if (loggingEnabled) {
        var console = $('#console');
        console.append(msg + "\n");
        console.scrollTop(console[0].scrollHeight - console.outerHeight());
    }
}

/**
 * Hack to map touch into mouse events, from
 * http://stackoverflow.com/questions/5186441/javascript-drag-and-drop-for-touch-devices
 */
function touchHandler(event) {
    var touches = event.changedTouches,
    first = touches[0],
    type = "";

    switch (event.type) {
        case "touchstart": type="mousedown"; break;
        case "touchmove": type="mousemove"; break;
        case "touchend": type="mouseup"; break;
        default: return;
    }

    var simulatedEvent = document.createEvent("MouseEvent");
    simulatedEvent.initMouseEvent(type, true, true, window, 1,
                                  first.screenX, first.screenY,
                                  first.clientX, first.clientY, false,
                                  false, false, false, 0/*left*/, null);

    first.target.dispatchEvent(simulatedEvent);
    event.preventDefault();
}

/**
 * Returns the card orientation (one of [-4,-3,-2,-1,1,2,3,4]).
 * Here, card is the jquery selection corresponding to the card,
 * e.g. $("#card_24")
 */
function getOrient(card) {
    var orient = card.data("orient");
    if (orient == 0) {
        orient = 1;
    }
    return orient;
}

/* Changes the visible orientation the card */
function setOrientProperties(card, orient) {
    card.data("orient", orient);
    if (orient > 0) {
        card.prop("src", toResource(card.data("front")));
    } else {
        card.prop("src", toResource(card.data("back")));
    }

    if (Math.abs(orient) == 2) {
        card.addClass("rotated");
    } else {
        card.removeClass("rotated");
    }
}

/* Returns the x position of the card snapped-to the grid. */
function gridX(card) {
    var offset = card.offset();
    var left = offset.left - heightOf(card.data("stack_index"));
    return parseInt((left + kGridSpacing/2) / kGridSpacing) * kGridSpacing;
}

/* Returns the y position of the card snapped-to the grid. */
function gridY(card) {
    var offset = card.offset();
    var tp = offset.top - heightOf(card.data("stack_index"));
    if (card.hasClass("rotated")) {
        tp -= parseInt(card.css("margin-top"));
    }
    return parseInt((tp + kGridSpacing/2) / kGridSpacing) * kGridSpacing;
}

/**
 * Produces the unique 32-bit identifier for an (x, y) tuple
 * that the websocket server uses to specify a position.
 */
function gridKey(x, y) {
    return ((x + kGridSpacing/2) / kGridSpacing) |
           ((y + kGridSpacing/2) / kGridSpacing) << 16;
}

/* Extracts x-value from key as produced by gridKey. */
function keyToX(key) {
    return (key & 0xffff) * kGridSpacing;
}

/* Extracts y-value from key as produced by gridKey. */
function keyToY(key) {
    return (key >> 16) * kGridSpacing;
}

/* Identical to gridKey() but taking a jquery selection. */
function cardToGridKey(card) {
    return gridKey(gridX(card), gridY(card));
}

/**
 * Broadcasts the location of card to other users, so that their clients
 * can draw a phantom box where the card is being dragged. If entireStack
 * is set to True, the phantom box will encompass the entire stack.
 */
function phantomUpdate(card, entireStack) {
    if (card.hasClass("inHand")) {
        return;
    }
    var stack_height = heightOf(card.data("stack_index"));
    if (entireStack) {
        var x = gridX(card);
        var y = gridY(card);
        var w = card.outerWidth() + stack_height;
        var h = card.outerHeight() + stack_height;
    } else if (startPhantomLocation == cardToGridKey(card)) {
        // In this case the card is still close to the stack.
        var x = gridX(card) + stack_height;
        var y = gridY(card) + stack_height;
        var w = card.outerWidth();
        var h = card.outerHeight();
    } else {
        // In this case the card has been dragged off the stack.
        var x = gridX(card);
        var y = gridY(card);
        var w = card.outerWidth();
        var h = card.outerHeight();
    }
    ws.send("broadcast",
        {
            "subtype": "phantomupdate",
            "hide": false,
            "uuid": uuid,
            "name": user,
            "left": x,
            "top": y,
            "orient": getOrient(card),
            "width": w,
            "height": h,
        });
}

/* Broadcasts that the user is done dragging the card. */
function phantomDone() {
    ws.send("broadcast",
        {
            "subtype": "phantomupdate",
            "hide": true,
            "uuid": uuid,
        });
}

/* Sets and broadcasts the visible orientation of the card. */
function changeOrient(card, orient) {
    setOrientProperties(card, orient);
    phantomUpdate(card);

    var cardId = parseInt(card.prop("id").substr(5));
    var dest_type = "board";
    var dest_prev_type = "board";
    var dest_key = cardToGridKey(card);
    if (card.hasClass("inHand")) {
        dest_type = "hands";
        dest_key = user;
        dest_prev_type = "hands";
    }
    log("Sending orient change.");
    showSpinner();
    ws.send("move", {move: {card: cardId,
                            dest_type: dest_type,
                            dest_key: dest_key,
                            dest_prev_type: dest_type,
                            dest_orient: orient}});
    phantomDone();
}

/* Toggles and broadcasts card rotation. */
function rotateCard(card) {
    var orient = getOrient(card);
    if (Math.abs(orient) == 1) {
        orient *= 2;
    } else if (Math.abs(orient) == 2) {
        orient /= 2;
    } else {
        log("Card is not in supported orientation: at " + orient);
        return;
    }
    changeOrient(card, orient);
    if (Math.abs(orient) > 1) {
        $(".hovermenu")
            .children("img")
            .height(kCardHeight * kHoverTapRatio)
            .width(kCardWidth * kHoverTapRatio)
            .addClass("hoverRotate");
    } else {
        $(".hovermenu")
            .children("img")
            .removeClass("hoverRotate")
            .height(kCardHeight * kHoverCardRatio)
            .width(kCardWidth * kHoverCardRatio);
    }
}

/* Toggles and broadcasts card face up/down. */
function flipCard(card) {
    changeOrient(card, -getOrient(card));
    var url = getOrient(card) > 0 ? card.data("front_full") : card.data("back");
    $(".hovermenu").children("img").prop("src", url);
}

/* Requests a stack flip from the server. */
function flipStack(topCard) {
    if (topCard.hasClass("inHand")) {
        flipCard(topCard);
        return;
    }
    var dest_key = cardToGridKey(topCard);
    phantomUpdate(topCard, true);
    showSpinner();
    ws.send("stackop", {op_type: "reverse",
                        dest_type: "board",
                        dest_key: dest_key});
    phantomDone();
}

function shuffleStackConfirm() {
    var node = $(".shufstackconfirm");
    node.removeClass("shufstackconfirm");
    node.removeClass("hover");
    node.addClass("confirm");
    node.data("key", "shufstack");
    node.html("You&nbsp;sure?");
    return true;
}

/* Requests a stack shuffle from the server. */
function shuffleStack(topCard) {
    if (topCard.hasClass("inHand")) {
        return;
    }
    var dest_key = cardToGridKey(topCard);
    phantomUpdate(topCard, true);
    showSpinner();
    ws.send("stackop", {op_type: "shuffle",
                        dest_type: "board",
                        dest_key: dest_key});
    phantomDone();
}

/* Garbage collects older hovermenu image. */
function removeHoverMenu() {
    hoverCardId = null;
    var old = $(".hovermenu");
    old.hide();
    setTimeout(function() { old.remove(); }, 1000);
}

/**
 * Displays a large version of the card image at the center of the screen,
 * along with controls for the stack.
 */
function showHoverMenu(card) {
    hoverCardId = card.prop("id");
    var old = $(".hovermenu");
    var oldimg = $(".hovermenu img");
    var numCards = parseInt(card.data("stack_index")) + 1;
    var url = getOrient(card) > 0 ? card.data("front_full") : card.data("back");
    var src = toResource(url);
    var flipStr = getOrient(card) > 0 ? "Cover" : "Reveal";
    var tapStr = card.hasClass("rotated") ? "Untap" : "Tap";
    var imgCls = '';
    if (card.hasClass("rotated")) {
        log("rotated card");
        var height = kCardHeight * kHoverTapRatio;
        var width = kCardWidth * kHoverTapRatio;
        imgCls = "hoverRotate";
    } else {
        log("vertical card");
        var height = kCardHeight * kHoverCardRatio;
        var width = kCardWidth * kHoverCardRatio;
    }
    var html = ('<div class="hovermenu">'
        + '<img class="' + imgCls + '" style="height: '
        + height + 'px; width: ' + width + 'px;"'
        + ' src="' + src + '"></img>'
        + '<ul class="hovermenu" style="float: right; width: 50px;">'
        + '<span class="header" style="margin-left: -190px">&nbsp;ACTION</span>"'
        + '<li class="top" style="margin-top: 10px; margin-left: -190px"'
        + ' data-key=flip>' + flipStr + '</li>'
        + '<li style="margin-top: 10px; margin-left: -190px"'
        + ' class="boardonly" data-key="rotate">' + tapStr + '</li>'
        + '<li style="margin-top: 10px; font-size: 30pt;'
        + ' margin-left: -190px" class="boardonly bulk"'
        + ' data-key="flipstack">Flip&nbsp;All</li>'
        + '<li style="margin-top: 10px; font-size: 30pt;'
        + ' margin-left: -190px" class="boardonly bulk shufstackconfirm"'
        + ' data-key="shufstackconfirm">Shuffle</li>'
        + '</ul>'
        + '<div class="hovernote"><span>' + numCards + ' cards in stack</span></div>'
        + '</div>');
    var newNode = $(html).appendTo("body");
    if (card.hasClass("inHand")) {
        $(".boardonly").addClass("disabled");
        $(".hovernote").hide();
    } else if (numCards > 1) {
        $(".hovernote").show();
        $(".boardonly").removeClass("disabled");
    } else {
        $(".hovernote").hide();
        $(".boardonly").removeClass("disabled");
        $(".bulk").addClass("disabled");
    }
    var newImg = newNode.children("img");
    newNode.width(805);
    newNode.height(kCardHeight * kHoverCardRatio);
    newNode.css("margin-left", - ($(".hovermenu").outerWidth() / 2));
    newNode.css("margin-top", - ($(".hovermenu").outerHeight() / 2));
    if (old.filter(':visible').length > 0) {
        if (oldimg.prop("src") == newImg.prop("src")) {
            oldimg.fadeOut();
        }
        newNode.fadeIn();
    } else {
        newNode.show();
    }
    setTimeout(function() { old.remove(); }, 1200);
}

/* Moves a card offscreen - used for hiding hands of other players. */
function moveOffscreen(card) {
    var kOffscreenY = 2000;
    if (parseInt(card.css("top")) != kOffscreenY) {
        card.animate({
            left: card.css("left"),
            top: kOffscreenY,
            opacity: 0,
        }, animationLength);
    }
}

/* Redraws user's hand given an array of cards present. */
function renderHandStack(hand) {
    handCache = hand;
    var kHandSpacing = 5;
    var kConsiderUnloaded = 20;
    var currentX = kHandSpacing;
    var handWidth = $("#hand").outerWidth();
    var cardWidth = kCardWidth + 8;
    var cardHeight = kCardHeight + 8;
    var handHeight = cardHeight + 2 * kHandSpacing;
    var collapsedHandSpacing = Math.min(
        kHandSpacing + cardWidth,
        (handWidth - cardWidth - kHandSpacing * 2) / (hand.length - 1)
    );

    // Computes and sets height of hand necessary to hold cards.
    for (i in hand) {
        if (i == hand.length - 1) {
            break;
        }
        var cd = $("#card_" + hand[i]);
        if (!$("#hand").hasClass("collapsed")) {
            currentX += cardWidth + kHandSpacing;
            if (currentX + cardWidth + 10 > handWidth) {
                handHeight += cardHeight + kHandSpacing;
                currentX = kHandSpacing;
            }
        }
    }
    handHeight = Math.min(handHeight, $("#arena").outerHeight() - cardHeight * 1.2);
    $("#hand").height(handHeight);

    var currentX = kHandSpacing;
    var currentY = $("#hand").position().top - $(window).scrollTop() + kHandSpacing;
    var collapsed = $("#hand").hasClass("collapsed");

    XXX_jitter *= -1;

    for (i in hand) {
        var cd = $("#card_" + hand[i]);
        if (!collapsed) {
            if (currentX + cardWidth + 10 > handWidth) {
                currentY += cardHeight + kHandSpacing;
                currentX = kHandSpacing;
            }
        }
        cd.addClass("inHand");
        cd.css("zIndex", kHandZIndex + parseInt(i));
        cd.data("stack_index", kHandZIndex + i);
        var xChanged = parseInt(currentX) != parseInt(cd.css('left'));
        var yChanged = parseInt(currentY) != parseInt(cd.css('top'));
        if (xChanged || yChanged) {
            cd.animate({
                left: currentX + (xChanged ? 0 : XXX_jitter),
                top: currentY + (yChanged ? 0 : XXX_jitter),
                opacity: 1.0,
            }, animationLength);
        }
        if ($("#hand").hasClass("collapsed")) {
            currentX += collapsedHandSpacing;
        } else {
            currentX += cardWidth + kHandSpacing;
        }
    }
}

/* Forces a re-render of the hand after a handCache update. */
function redrawHand() {
    if (handCache) {
        renderHandStack(handCache);
    }
}

$(document).ready(function() {
    document.addEventListener("touchstart", touchHandler, true);
    document.addEventListener("touchmove", touchHandler, true);
    document.addEventListener("touchend", touchHandler, true);
    document.addEventListener("touchcancel", touchHandler, true);
    var connected = false;

    function initCards() {
        $(".card").disableSelection();

        $(".card").each(function(index, card) {
            setOrientProperties($(card), getOrient($(card)));
        });

        $(".card").draggable({
            containment: $("#arena"),
            refreshPositions: true,
            grid: [kGridSpacing, kGridSpacing],
        });

        $(".card").bind("dragstart", function(event, ui) {
            dragging = true;
            removeHoverMenu();
            var target = $(event.currentTarget);
            if (!target.hasClass("inHand")) {
                deactivateHand();
            }
            /* Slow on mobile.
            target.css("zIndex", kDraggingZIndex);
            */
            lastPhantomLocation = startPhantomLocation = cardToGridKey(target);
            phantomUpdate(target);
            ws.send("broadcast", {"subtype": "dragstart", "card": target.prop("id")});
        });

        $(".card").bind("drag", function(event, ui) {
            var target = $(event.currentTarget);
            dragging = true;
            target.stop();
            var dest_key = cardToGridKey(target);
            if (dest_key != lastPhantomLocation) {
                lastPhantomLocation = dest_key;
                phantomUpdate(target);
            }
        });

        $(".card").bind("dragstop", function(event, ui) {
            dragging = false;
            $(".card").removeClass("highlight");
            phantomDone();
            var card = $(event.currentTarget);
            card.css("zIndex", kDraggingZIndex);
            var cardId = parseInt(card.prop("id").substr(5));
            var orient = card.data("orient");
            if (card.hasClass("inHand")) {
                var dest_prev_type = "hands";
            } else {
                var dest_prev_type = "board";
            }
            if ($("#hand").hasClass("active")) {
                deferDeactivateHand();
                var dest_type = "hands";
                var dest_key = user;
            } else {
                var dest_type = "board";
                var x = gridX(card);
                var y = gridY(card);
                var dest_key = gridKey(x, y);
                if (dest_prev_type == "hands") {
                    removeFromArray(handCache, cardId);
                    redrawHand();
                }
                card.css("zIndex", localMaxZ);
                localMaxZ += 1;
            }
            log("Sending card move.");
            showSpinner();
            ws.send("move", {move: {card: cardId,
                                    dest_prev_type: dest_prev_type,
                                    dest_type: dest_type,
                                    dest_key: dest_key,
                                    dest_orient: orient}});
        });

        $(".card").mousedown(function(event) {
            var card = $(event.currentTarget);
            draggingCard = card;
            $(".card").removeClass("highlight");
            if (!card.hasClass("inHand") || !$("#hand").hasClass("collapsed")) {
                draggingCard.addClass("highlight");
            }
        });

        $(".card").mouseup(function(event) {
            var card = $(event.currentTarget);
            if (!dragging) {
                if (card.hasClass("inHand")
                        && $("#hand").hasClass("collapsed")) {
                    // Expands the hand if a card is clicked on in collapsed mode.
                    $("#hand").removeClass("collapsed");
                    redrawHand();
                } else if (hoverCardId != card.prop("id")) {
                    showHoverMenu(card);
                } else {
                    removeHoverMenu();
                    $(".card").removeClass("highlight");
                }
            }
            disableArenaEvents = true;
            dragging = false;
        });
    }

    /* Discards and redownloads all local state from the server. */
    function reset(state) {
        animationLength = 0;
        log("Reset all local state.");
        $(".uuid_phantom").remove();
        $(".card").remove();
        resourcePrefix = state.resource_prefix;
        handCache = null;

        function createImageNode(state, cid, stack_index) {
            var front_url = state.urls_small[cid] || state.urls[cid];
            var back_url = state.back_urls[cid] || state.default_back_url;
            var url = front_url;
            if (state.orientations[cid] == undefined) {
                state.orientations[cid] = -1;
            }
            if (state.orientations[cid] < 0) {
                url = back_url;
            }
            var img = '<img style="z-index: ' + state.zIndex[cid] + '; display: none"'
                + ' id="card_' + cid + '"'
                + ' data-orient="' + state.orientations[cid] + '"'
                + ' data-front="' + front_url + '"'
                + ' data-front_full="' + state.urls[cid] + '"'
                + ' data-back="' + back_url + '"'
                + ' data-stack_index="' + stack_index + '"'
                + ' class="card" src="' + toResource(url) + '">'
            $("#arena").append(img);
        }

        // Recreates the board.
        for (pos in state.board) {
            var stack = state.board[pos];
            for (z in stack) {
                var cid = stack[z];
                var x = keyToX(pos);
                var y = keyToY(pos);
                createImageNode(state, cid, z);
                var card = $("#card_" + cid);
                card.animate({
                    left: x + heightOf(z),
                    top: y + heightOf(z),
                }, animationLength);
            }
        }

        // Recreates the hand.
        for (player in state.hands) {
            var hand = state.hands[player];
            for (i in hand) {
                createImageNode(state, hand[i], i);
            }
            if (player == user) {
                renderHandStack(hand, false);
            } else {
                for (i in hand) {
                    moveOffscreen($("#card_" + hand[i]));
                }
            }
        }
        $(".card").fadeIn();
        initCards();
        animationLength = kAnimationLength;
    }

    ws = $.websocket("ws:///" + hostname + ":" + kWSPort + "/kansas", {
        open: function() { alert("open"); },
        close: function() { alert("close"); },
        events: {
            connect_resp: function(e) {
                hideSpinner();
                log("Connected: " + e.data);
                $(".connected").show();
                reset(e.data[0]);
            },

            resync_resp: function(e) {
                hideSpinner();
                reset(e.data[0]);
            },

            broadcast_resp: function(e) {
                /* Ignores acks for the phantom update messages we broadcast. */
            },

            error: function(e) {
                log("Server Error: " + e.msg);
                alert("Server Error: " + e.msg);
            },

            reset: function(e) {
                hideSpinner();
                reset(e.data[0]);
            },

            stackupdate: function(e) {
                hideSpinner();
                log("Stack update: " + JSON.stringify(e.data));
                var x = keyToX(e.data.op.dest_key);
                var y = keyToY(e.data.op.dest_key);

                /* Temporarily hides each card in the stack. */
                for (i in e.data.z_stack) {
                    var cd = $("#card_" + e.data.z_stack[i]);
                    cd.hide();
                }

                /* Redraws and shows each card in the stack. */
                for (i in e.data.z_stack) {
                    var cd = $("#card_" + e.data.z_stack[i]);
                    cd.css("left", x + heightOf(i));
                    cd.css("top", y + heightOf(i));
                    cd.data("stack_index", i);
                    cd.css("zIndex", e.data.z_index[i]);
                    localMaxZ = Math.max(localMaxZ, e.data.z_index[i]);
                    setOrientProperties(cd, e.data.orient[i]);
                    cd.fadeIn();
                }
            },

            update: function(e) {
                hideSpinner();
                log("Update: " + JSON.stringify(e.data));
                var target = $("#card_" + e.data.move.card);

                if (e.data.move.dest_type == "board") {

                    setOrientProperties(target, e.data.move.dest_orient);
                    var lastindex = e.data.z_stack.length - 1;
                    var x = (e.data.move.dest_key & 0xffff) * kGridSpacing;
                    var y = (e.data.move.dest_key >> 16) * kGridSpacing;
                    if (removeFromArray(handCache, e.data.move.card)) {
                        redrawHand();
                    }
                    for (i in e.data.z_stack) {
                        if (i == lastindex) {
                            continue; // Skips last element for later handling.
                        }
                        var cd = $("#card_" + e.data.z_stack[i]);
                        cd.css("left", x + heightOf(i));
                        cd.css("top", y + heightOf(i));
                        cd.data("stack_index", i);
                    }
                    target.data("stack_index", lastindex);
                    target.css("zIndex", e.data.z_index);
                    localMaxZ = Math.max(localMaxZ, e.data.z_index);
                    var newX = x + heightOf(lastindex);
                    var newY = y + heightOf(lastindex);
                    var xChanged = parseInt(newX) != parseInt(target.css('left'));
                    var yChanged = parseInt(newY) != parseInt(target.css('top'));
                    XXX_jitter *= -1;
                    target.animate({
                        left: newX + (xChanged ? 0 : XXX_jitter),
                        top: newY + (yChanged ? 0 : XXX_jitter),
                        opacity: 1.0,
                        avoidTransforms: target.hasClass("rotated"),
                    }, 'fast');
                    target.removeClass("inHand");

                } else if (e.data.move.dest_type == "hands") {

                    setOrientProperties(target, e.data.move.dest_orient);
                    if (e.data.move.dest_key == user) {
                        target.addClass("inHand");
                        renderHandStack(e.data.z_stack, true);
                    } else {
                        moveOffscreen(target);
                    }

                } else {
                    log("WARN: unknown dest type: " + e.data.move.dest_type);
                }
            },

            broadcast_message: function(e) {
                switch (e.data.subtype) {
                    case "dragstart":
                        $("#" + e.data.card).css("opacity", "0.7");
                        break;
                    case "phantomupdate":
                        var phantom = $("#" + e.data.uuid);
                        if (phantom.length == 0) {
                            var node = '<div class="uuid_phantom" id="' + e.data.uuid + '" style="position: fixed; border: 3px solid orange; pointer-events: none; border-radius: 5px; z-index: ' + (kPhantomZIndex) + '; font-family: sans;"><span style="background-color: orange; padding-right: 2px; padding-bottom: 2px; border-radius: 2px; color: white; margin-top: -2px !important; margin-left: -1px;">' + e.data.name + '</span></div>';
                            $("#arena").append(node);
                            phantom = $("#" + e.data.uuid);
                        }
                        if (e.data.hide) {
                            phantomHideQueued[e.data.uuid] = true;
                            setTimeout(function() {
                                if (phantomHideQueued[e.data.uuid]) {
                                    phantom.hide();
                                    phantomHideQueued[e.data.uuid] = false;
                                }
                            }, 1500);
                        } else {
                            phantomHideQueued[e.data.uuid] = false;
                            phantom.stop();
                            phantom.css('opacity', 1.0);
                            setOrientProperties(phantom, e.data.orient);
                            phantom.width(e.data.width - 6);
                            phantom.height(e.data.height - 6);
                            phantom.css("left", e.data.left);
                            phantom.css("top", e.data.top);
                            phantom.show();
                        }
                        break;
                }
                log("Recv broadcast: " + JSON.stringify(e));
            },
            _default: function(e) {
                log("Unknown response: " + JSON.stringify(e));
            },
        },
    });

    function tryConnect() {
        if (!connected) {
            showSpinner();
            ws.send("connect", {user: user, gameid: gameid});
            connected = true;
        }
    }

    $("#sync").mouseup(function(e) {
        showSpinner();
        ws.send("resync");
    });

    $("#reset").mouseup(function(e) {
        if (confirm("Are you sure you want to reset the game?")) {
            showSpinner();
            ws.send("reset");
        }
    });

    $("#debug").mouseup(function(e) {
        $("#console").toggle();
        loggingEnabled = !loggingEnabled;
    });

    $("#hand").droppable({
        over: function(event, ui) {
            if (dragging) {
                var card = parseInt(draggingCard.prop("id").substr(5));
                removeFromArray(handCache, card);
            }
            activateHand();
            if (dragging && !draggingCard.hasClass("inHand")) {
                redrawHand();
            }
        },
        out: function(event, ui) {
            if (dragging) {
                var card = parseInt(draggingCard.prop("id").substr(5));
                removeFromArray(handCache, card);
            }
            deactivateHand();
            if (dragging && !$("#hand").hasClass("collapsed")) {
                $("#hand").addClass("collapsed");
                redrawHand();
            }
        },
        tolerance: "touch",
    });

    $("#arena").disableSelection();
    $("body").disableSelection();
    $("html").disableSelection();
    $("#hand").disableSelection();

    $("#arena").mouseup(function(event) {
        if (disableArenaEvents) {
            log("arena mouseup: skipping event");
            disableArenaEvents = false;
        } else {
            log("arena mouseup");
            removeHoverMenu();
            $("#hand").addClass("collapsed");
            redrawHand();
            $(".card").removeClass("highlight");
        }
    });

    $("#arena").mousedown(function(event) {
        if (disableArenaEvents) {
            log("arena mousedown: skipping event");
            disableArenaEvents = false;
        } else {
            log("arena mousedown");
            deactivateHand();
        }
    });

    $("#hand").mouseup(function(event) {
        log("hand click: show hand");
        if ($("#hand").hasClass("collapsed")) {
            $("#hand").removeClass("collapsed");
            redrawHand();
        }
    });

    $(".hovermenu li").live('mousedown', function(event) {
        var target = $(event.currentTarget);
        if (!target.hasClass("poisoned")) {
            target.addClass("hover");
        }
    });

    $(".hovermenu li").live('mouseup', function(event) {
        var target = $(event.currentTarget);
        if (target.hasClass("poisoned")) {
            return;
        }
        disableArenaEvents = true;
        var eventTable = {
            'flip': flipCard,
            'rotate': rotateCard,
            'flipstack': flipStack,
            'shufstack': shuffleStack,
            'shufstackconfirm': shuffleStackConfirm,
        };
        var keepButton = eventTable[target.data("key")](draggingCard);
        if (keepButton) {
            $(".hovermenu li").not(target).addClass("disabled");
        } else {
            $(".hovermenu li").addClass("disabled");
            target.addClass("poison-source");
            $(".card").removeClass("highlight");
            $(".hovermenu").fadeOut();
            hoverCardId = null;
        }
        return false; /* Necessary for shufstackconfirm. */
    });

    $(window).resize(function() { redrawHand(); });
    setTimeout(tryConnect, 1000);
});

// vim: et sw=4
