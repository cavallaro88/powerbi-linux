// SPDX-License-Identifier: GPL-3.0-or-later
// Called only after the original Options tab control finishes loading.
function powerbiOptionsLayout(control) {
    var frame = $("#modalDialog"), body = $(".o-group-body"), tabs = $(".o-group-tabs"), pane = control.panes.element;
    frame.addClass("pbi-options");
    $("<style>").text(
        ".pbi-options,.pbi-options *{-moz-user-select:none;user-select:none}" +
        ".pbi-options input,.pbi-options textarea,.pbi-options [contenteditable=true],.pbi-options [contenteditable=true] *{-moz-user-select:text;user-select:text}" +
        ".pbi-options .modal-main{width:100%;height:100%}" +
        ".pbi-options .o-group-header,.pbi-options .o-group-footer{flex-shrink:0;width:100%!important}" +
        ".pbi-options .o-group-body{min-height:0!important;overflow:hidden}" +
        ".pbi-options .o-root-options,.pbi-options .o-group-options,.pbi-options .o-group-tabControl{height:100%!important;width:100%!important;box-sizing:border-box}" +
        ".pbi-options .o-group-tabControl{display:flex}" +
        ".pbi-options .o-group-tabs{flex:0 1 220px;max-width:35%;overflow:auto;box-sizing:border-box}" +
        ".pbi-options .o-group-tabs>.role-tabGroup{height:auto!important;max-height:none!important;overflow:visible}" +
        ".pbi-options .o-group-tabContainers{flex:1;min-width:0;width:auto!important;box-sizing:border-box}" +
        ".pbi-options>.ui-resizable-handle{z-index:1000}"
    ).appendTo("head");
    function fit() {
        frame.css({width:innerWidth,height:innerHeight});
        var bottom = body[0].getBoundingClientRect().bottom;
        tabs.add(pane).each(function () {
            this.style.maxHeight = Math.max(0,bottom-this.getBoundingClientRect().top)+"px";
        });
    }
    frame.css({width:Math.min(1000,screen.availWidth-32),height:Math.min(800,screen.availHeight-32)});
    ClientShared.ModalDialog._resizeHost(frame);
    $(window).on("resize",function () {setTimeout(fit,0);});
    setTimeout(fit,0);
}
