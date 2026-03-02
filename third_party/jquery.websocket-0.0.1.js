/*
 * jQuery Web Sockets Plugin v0.0.1
 * http://code.google.com/p/jquery-websocket/
 *
 * This document is licensed as free software under the terms of the
 * MIT License: http://www.opensource.org/licenses/mit-license.php
 * 
 * Copyright (c) 2010 by shootaroo (Shotaro Tsubouchi).
 *
 * Modified by Eric Liang (c 2013) to support futures.
 */

(function($){
$.extend({
    websocketSettings: {
        open: function(){},
        close: function(){},
        message: function(){},
        options: {},
        events: {}
    },
    websocket: function(url, s) {
        var ws = WebSocket ? new WebSocket( url ) : {
            send: function(m){ return false },
            close: function(){}
        };
        ws.sendCount = 0;
        ws.recvCount = 0;
        ws.lastSent = new Date();
        ws.lastAction = new Date();
        ws._pendingMessages = [];
        ws._settings = $.extend($.websocketSettings, s);
        $(ws)
            .bind('open', function(e) {
                while (ws._pendingMessages.length && ws.readyState === 1) {
                    ws._send(ws._pendingMessages.shift());
                }
                $.websocketSettings.open.call(this, e);
            })
            .bind('close', $.websocketSettings.close)
            .bind('message', $.websocketSettings.message)
            .bind('message', function(e) {
                var m = JSON.parse(e.originalEvent.data);
                var h = $.websocketSettings.events[m.type];
                var def = $.websocketSettings.events['_default'];
                var fut = $.websocketSettings.events['_future_router'];
                ws.recvCount += 1;
                ws.lastAction = new Date();
                if (m.future_id && fut) {
                    fut.call(this, m);
                } else if (h) {
                    h.call(this, m)
                } else if (def) {
                    def.call(this, m)
                }
            });
        ws._send = ws.send;
        ws.send = function(type, data, future_id) {
            ws.sendCount += 1;
            if (ws.lastAction > ws.lastSent) {
                ws.lastAction = new Date();
            }
            ws.lastSent = new Date();
            var m = {type: type};
            m = $.extend(true, m, $.extend(true, {}, $.websocketSettings.options, m));
            if (data) m['data'] = data;
            if (future_id) m['future_id'] = future_id;
            var payload = JSON.stringify(m);
            if (ws.readyState === 0) {
                ws._pendingMessages.push(payload);
                return false;
            }
            if (ws.readyState !== 1) {
                return false;
            }
            return this._send(payload);
        }
        $(window).unload(function(){ ws.close(); ws = null });
        return ws;
    }
});
})(jQuery);
