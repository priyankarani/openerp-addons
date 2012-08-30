openerp.mail = function(session) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail = session.mail = {};

    openerp_mail_followers(session, mail);        // import mail_followers.js

    /**
     * ------------------------------------------------------------
     * FormView
     * ------------------------------------------------------------
     * 
     * Override of formview do_action method, to catch all return action about
     * mail.compose.message. The purpose is to bind 'Send by e-mail' buttons
     * and redirect them to the Chatter.
     */

    session.web.FormView = session.web.FormView.extend({
        // #FIXME TODO: CHECK WITH NEW BRANCH
        do_action: function(action, on_close) {
            if (action.res_model == 'mail.compose.message' && this.fields && this.fields.message_ids && this.fields.message_ids.view.get("actual_mode") != 'create') {
                var record_thread = this.fields.message_ids;
                var thread = record_thread.thread;
                thread.instantiate_composition_form('comment', true, false, 0, action.context);
                return false;
            }
            else {
                return this._super(action, on_close);
            }
        },
    });

    /**
     * ------------------------------------------------------------
     * ChatterUtils
     * ------------------------------------------------------------
     * 
     * This class holds a few tools method that will be used by
     * the various Chatter widgets.
     *
     * Some regular expressions not used anymore, kept because I want to
     * - (^|\s)@((\w|@|\.)*): @login@log.log, supports inner '@' for
     *   logins that are emails
     *      1. '(void)'
     *      2. login@log.log
     * - (^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]: [ir.attachment,3|My Label],
     *   for internal links to model ir.attachment, id=3, and with
     *   optional label 'My Label'. Note that having a '|Label' is not
     *   mandatory, because the regex should still be correct.
     *      1. '(void)'
     *      2. 'ir'
     *      3. 'attachment'
     *      4. '3'
     *      5. 'My Label'
     */

    mail.ChatterUtils = {

        /** get an image in /web/binary/image?... */
        get_image: function(session_prefix, session_id, model, field, id) {
            return session_prefix + '/web/binary/image?session_id=' + session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },

        /** checks if tue current user is the message author */
        is_author: function (widget, message_user_id) {
            return (widget.session && widget.session.uid != 0 && widget.session.uid == message_user_id);
        },

        /** Replaces some expressions
         * - :name - shortcut to an image
         */
        do_replace_expressions: function (string) {
            var self = this;
            var icon_list = ['al', 'pinky']
            /* special shortcut: :name, try to find an icon if in list */
            var regex_login = new RegExp(/(^|\s):((\w)*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var icon_name = regex_res[2];
                if (_.include(icon_list, icon_name))
                    string = string.replace(regex_res[0], regex_res[1] + '<img src="/mail/static/src/img/_' + icon_name + '.png" width="22px" height="22px" alt="' + icon_name + '"/>');
                regex_res = regex_login.exec(string);
            }
            return string;
        },
    };


    /**
     * ------------------------------------------------------------
     * ComposeMessage widget
     * ------------------------------------------------------------
     * 
     * This widget handles the display of a form to compose a new message.
     * This form is an OpenERP form_view, build on a mail.compose.message
     * wizard.
     */

    mail.ComposeMessage = session.web.Widget.extend({
        template: 'mail.compose_message',
        
        /**
         * @param {Object} parent parent
         * @param {Object} [options] 
         * @param {Object} [options.context] context
         * @param {String} [context.res_model] res_model of document [REQUIRED]
         * @param {Number} [context.res_id] res_id of record [REQUIRED]
         * @param {String} [context.composition_mode] mail.compose.message.mode
         *      (see composition wizard)
         * @param {Number} [context.msg_id] id of a message in case we are in
         *      reply mode
         */
        init: function (parent, options) {
            var self = this;
            this._super(parent);
            // options
            this.options = options || {};
            this.options.context = options.context || {};
            this.options.form_xml_id = options.form_xml_id || 'email_compose_message_wizard_form_chatter';
            this.options.form_view_id = options.form_view_id || false;
            // debug
            console.groupCollapsed('New ComposeMessage: model', this.options.context.default_res_model, ', id', this.options.context.default_res_id);
            console.log('context:', this.options.context);
            console.groupEnd();
        },

        start: function () {
            this._super.apply(this, arguments);
            // customize display: add avatar, clean previous content
            var user_avatar = mail.ChatterUtils.get_image(this.session.prefix, this.session.session_id, 'res.users', 'image_small', this.session.uid);
            this.$el.find('img.oe_mail_icon').attr('src', user_avatar);
            this.$el.find('div.oe_mail_msg_content').empty();
            // create a context for the dataset and default_get of the wizard
            var context = this._update_context({});
            console.log(context);
            this.ds_compose = new session.web.DataSetSearch(this, 'mail.compose.message', context);
            // find the id of the view to display in the chatter form
            var data_ds = new session.web.DataSetSearch(this, 'ir.model.data');
            return data_ds.call('get_object_reference', ['mail', this.options.form_xml_id]).pipe(this.proxy('create_form_view'));
        },

        /** Update the context of the compose wizard */
        _update_context: function (dest_context) {
            // TDE TOCHECK: after posting, back to reply mode !
            _.extend(dest_context, this.options.context, {
                'mail.compose.message.mode': this.options.context.composition_mode,
            });
            if (this.options.context.composition_mode == 'comment') {
                // _.extend(dest_context, {'default_res_id': this.options.res_id});
            }
            else if (this.options.context.composition_mode == 'reply') {
                _.extend(dest_context, {'active_id': this.options.context.msg_id});
            }
            return dest_context
        },

        /** Create a FormView, then append it to the to widget DOM. */
        create_form_view: function (form_view_id) {
            this.options.form_view_id = form_view_id[1] || false;
            var self = this;
            // destroy previous form_view if any
            if (this.form_view) { this.form_view.destroy(); }
            // create the FormView
            this.form_view = new session.web.FormView(this, this.ds_compose, this.options.form_view_id, {
                action_buttons: false,
                pager: false,
                initial_mode: 'edit',
                disable_autofocus: true,
            });
            // add the form, bind events, activate the form
            var msg_node = this.$el.find('div.oe_mail_msg_content');
            return $.when(this.form_view.appendTo(msg_node)).pipe(function() {
                self.bind_events();
                self.form_view.do_show();
            });
        },

        /**
         * Reinitialize the widget field values to the default values. The
         * purpose is to avoid to destroy and re-build a form view. Default
         * values are therefore given as for an on_change. */
        refresh: function (options_update_values) {
            var self = this;
            this.options.context = _.extend(this.options.context, options_update_values || {});
            if (! this.form_view) return;
            this.ds_compose.context = this._update_context(this.ds_compose.context);
            return this.ds_compose.call('default_get', [
                ['subject', 'body_text', 'body', 'attachment_ids', 'partner_ids', 'composition_mode',
                    'model', 'res_id', 'parent_id', 'content_subtype'],
                this.ds_compose.get_context(),
            ]).then( function (result) { self.form_view.on_processed_onchange({'value': result}, []); });
        },

        /**
         * Override-hack of do_action: clean the form */
        do_action: function(action, on_close) {
            console.log('compose_message do_action', action, on_close);
            return this._super(action, on_close);
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            // event: click on 'Attachment' icon-link that opens the dialog to
            // add an attachment.
            this.$el.on('click', 'button.oe_mail_compose_message_attachment', function (event) {
                event.stopImmediatePropagation();
            });
        },
    }),

    /** 
     * ------------------------------------------------------------
     * Thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a thread of messages. The
     * [thread_level] parameter sets the thread level number:
     * - root message
     * - - sub message (parent_id = root message)
     * - - - sub sub message (parent id = sub message)
     * - - sub message (parent_id = root message)
     * This widget has 2 ways of initialization, either you give records
     * to be rendered, either it will fetch [limit] messages related to
     * [res_model]:[res_id].
     */

    mail.Thread = session.web.Widget.extend({
        template: 'mail.thread',

        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         * @param {String} [options.res_model] res_model of document [REQUIRED]
         * @param {Number} [options.res_id] res_id of record [REQUIRED]
         * @param {Number} [options.uid] user id [REQUIRED]
         * @param {Bool}   [options.parent_id=false] parent_id of message
         * @param {Number} [options.thread_level=0] number of levels in the thread
         *      (only 0 or 1 currently)
         * @param {Bool}   [options.is_wall=false] thread is displayed in the wall
         * @param {Number} [options.msg_more_limit=150] number of character to
         *      display before having a "show more" link; note that the text
         *      will not be truncated if it does not have 110% of the parameter
         *      (ex: 110 characters needed to be truncated and be displayed as
         *      a 100-characters message)
         * @param {Number} [options.limit=100] maximum number of messages to fetch
         * @param {Number} [options.offset=0] offset for fetching messages
         * @param {Number} [options.records=null] records to show instead of fetching messages
         */
        init: function(parent, options) {
            console.log(parent);
            this._super(parent);
            // options
            this.options = options || {};
            this.options.domain = options.domain || [];
            this.options.context = options.context || {};
            // check in parents, should not define multiple times
            this.options.context.res_model = options.context.res_model || 'mail.thread';
            this.options.context.res_id = options.context.res_id || false;
            this.options.context.parent_id = options.context.parent_id || false;
            this.options.thread_level = options.thread_level || 0;
            this.options.composer = options.composer || false;
            // TDE: not sure, here for testing / compatibility
            this.options.records = options.records || null;
            this.options.ids = options.ids || null;
            // datasets and internal vars
            this.ds_post = new session.web.DataSetSearch(this, this.options.context.res_model);
            this.ds_notif = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_msg = new session.web.DataSetSearch(this, 'mail.message');
            // display customization vars
            this.display = {};
            this.display.truncate_limit = options.truncate_limit || 250;
            this.display.show_header_compose = options.show_header_compose || false;
            this.display.show_reply = options.show_reply || false;
            this.display.show_delete = options.show_delete || false;
            this.display.show_hide = options.show_hide || false;
            this.display.show_reply_by_email = options.show_reply_by_email || false;
            this.display.show_more = options.show_more || false;
            // for search view
            this.search = {'domain': [], 'context': {}, 'groupby': {}}
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}}
            // debug
            console.groupCollapsed('New Thread: model', this.options.context.res_model, 'id', this.options.context.res_id, 'parent_id', this.options.context.parent_id, 'thread level', this.options.thread_level);
            console.log('records:', this.options.records, 'ids:', this.options.ids);
            console.log('options:', this.options);
            console.log('display:', this.display);
            console.groupEnd();
        },
        
        start: function() {
            this._super.apply(this, arguments);
            this.bind_events();
            // display messages: either given by parent, either fetch new ones
            if (this.options.records) var display_done = this.message_display(this.options.records);
            else var display_done = this.message_fetch();
            // customize display
            this.display_user_avatar();
            $.when(display_done).then(this.proxy('do_customize_display'));
            // add message composition form view
            if (this.display.show_header_compose && this.options.composer) {
                var compose_done = this.instantiate_composition_form();
            }
            return display_done && compose_done;
        },

        /** Customize the display
         * - show_header_compose: show the composition form in the header */
        do_customize_display: function() {
            if (this.display.show_header_compose) { this.$el.find('div.oe_mail_thread_action').eq(0).show(); }
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            // event: click on 'more' at bottom of thread
            this.$el.find('button.oe_mail_button_more').click(function () {
                self.do_message_fetch();
            });
            // event: writing in basic textarea of composition form (quick reply)
            this.$el.find('textarea.oe_mail_compose_textarea').keyup(function (event) {
                var charCode = (event.which) ? event.which : window.event.keyCode;
                if (event.shiftKey && charCode == 13) { this.value = this.value+"\n"; }
                else if (charCode == 13) { return self.message_post(); }
            });
            // event: click on 'Reply' in msg
            this.$el.on('click', 'a.oe_mail_msg_reply', function (event) {
                event.preventDefault();
                event.stopPropagation();
                var act_dom = $(this).parents('li.oe_mail_thread_msg').eq(0).find('div.oe_mail_thread_action:first');
                act_dom.toggle();
            });
            // event: click on 'attachment(s)' in msg
            this.$el.on('click', 'a.oe_mail_msg_view_attachments', function (event) {
                event.preventDefault();
                event.stopPropagation();
                var act_dom = $(this).parent().parent().parent().find('.oe_mail_msg_attachments');
                act_dom.toggle();
            });
            // event: click on 'Delete' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_delete', function (event) {
                event.preventDefault();
                event.stopPropagation();
                if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).remove();
                return self.ds_msg.unlink([parseInt(msg_id)]);
            });
            // event: click on 'Hide' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_hide', function (event) {
                event.preventDefault();
                event.stopPropagation();
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).remove();
                return self.ds_notif.call('set_message_read', [parseInt(msg_id)]);
            });
            // event: click on "Reply by email" in msg side menu (email style)
            this.$el.on('click', 'a.oe_mail_msg_reply_by_email', function (event) {
                event.preventDefault();
                event.stopPropagation();
                var msg_id = event.srcElement.dataset.msg_id;
                if (! msg_id) return false;
                self.compose_message_widget.refresh({'composition_mode': 'reply', 'msg_id': parseInt(msg_id)});
            });
        },

        /**
         * Override-hack of do_action: automatically reload the chatter.
         * Normally it should be called only when clicking on 'Post/Send'
         * in the composition form. */
        do_action: function(action, on_close) {
            console.log('thread do_action', action, on_close, this);
            this.message_clean();
            this.message_fetch();
            if (this.compose_message_widget) {
                this.compose_message_widget.refresh(); }
            return this._super(action, on_close);
        },

        /** Instantiate the composition form, with parameters coming from thread parameters */
        instantiate_composition_form: function(mode, formatting, msg_id, context) {
            if (this.compose_message_widget) {
                this.compose_message_widget.destroy();
            }
            this.compose_message_widget = new mail.ComposeMessage(this, {
                'context': {
                    'default_model': this.options.context.res_model, 'default_res_id': this.options.context.res_id,
                    'composition_mode': mode || 'comment', 'msg_id': msg_id }
                });
            var composition_node = this.$el.find('div.oe_mail_thread_action');
            composition_node.empty();
            var compose_done = this.compose_message_widget.appendTo(composition_node);
            return compose_done;
        },

        /** Clean the thread */
        message_clean: function() {
            this.$el.find('div.oe_mail_thread_display').empty();
        },

        /** Fetch messages
         * @param {Array} additional_domain
         * @param {Object} additional_context
         */
        message_fetch: function (additional_domain, additional_context) {
            var self = this;
            // Update the domain and context
            this.search['domain'] = _.union(this.options.domain, this.search_results.domain);
            this.search['context'] = _.extend(this.options.context, this.search_results.context);
            if (additional_domain) var fetch_domain = this.search['domain'].concat(additional_domain);
            else var fetch_domain = this.search['domain'];
            if (additional_context) var fetch_context = _.extend(this.search['context'], additional_context);
            else var fetch_context = this.search['context'];

            // TODO first use: use IDS, otherwise set false

            var read_defer = this.ds_msg.call('message_read',
                [false, fetch_domain, this.options.thread_level, undefined, fetch_context]
                ).then(this.proxy('message_display'));
            return read_defer;
        },

        /* Display a list of records
         * - */
        message_display: function (records) {
            var self = this;
            var _expendable = false;
            console.groupCollapsed('message_display');
            console.log('records', records)
            console.groupEnd();
            _(records).each(function (record) {
                if (record.type == 'expandable') {
                    _expendable = true;
                    self.update_fetch_more(true);
                    self.fetch_more_domain = record.domain;
                    self.fetch_more_context = record.context;
                }
                else {
                    self.display_record(record);
                    self.thread = new mail.Thread(self, {
                        'context': { 'res_model': record.model, 'res_id': record.res_id, 'parent_id': record.id},
                        'show_header_compose': false, 'show_reply': self.options.thread_level > 1,
                        'show_hide': self.display.show_hide, 'show_delete': self.display.show_delete,
                        'uid': self.options.uid, 'records': record.child_ids, 'thread_level': (self.options.thread_level-1),
                    });
                    self.$el.find('li.oe_mail_thread_msg:last').append('<div class="oe_mail_thread_subthread"/>');
                    self.thread.appendTo(self.$el.find('div.oe_mail_thread_subthread:last'));
                }
            });
            if (! _expendable) {
                this.update_fetch_more(false);
            }
        },

        /** Displays a record and performs some formatting on the record :
         * - record.date: formatting according to the user timezone
         * - record.timerelative: relative time givein by timeago lib
         * - record.avatar: image url
         * - record.attachments[].url: url of each attachment
         * - record.is_author: is the current user the author of the record */
        display_record: function (record) {
            // formatting and additional fields
            record.date = session.web.format_value(record.date, {type:"datetime"});
            record.timerelative = $.timeago(record.date);
            if (record.type == 'email') {
                record.avatar = ('/mail/static/src/img/email_icon.png');
            } else {
                record.avatar = mail.ChatterUtils.get_image(this.session.prefix, this.session.session_id, 'res.partner', 'image_small', record.author_id[0]);
            }
            //TDE: FIX
            if (record.attachments) {
                for (var l in record.attachments) {
                    var url = self.session.origin + '/web/binary/saveas?session_id=' + self.session.session_id + '&model=ir.attachment&field=datas&filename_field=datas_fname&id='+records[k].attachments[l].id;
                    record.attachments[l].url = url;
                }
            }
            record.is_author = mail.ChatterUtils.is_author(this, record.author_user_id[0]);
            // render, add the expand feature
            var rendered = session.web.qweb.render('mail.thread.message', {'record': record, 'thread': this, 'params': this.options, 'display': this.display});
            $(rendered).appendTo(this.$el.children('div.oe_mail_thread_display:first'));
            this.$el.find('div.oe_mail_msg_record_body').expander({
                slicePoint: this.options.msg_more_limit,
                expandText: 'read more',
                userCollapseText: '[^]',
                detailClass: 'oe_mail_msg_tail',
                moreClass: 'oe_mail_expand',
                lessClass: 'oe_mail_reduce',
                });
        },

        /** Display 'show more' button */
        update_fetch_more: function (new_value) {
            if (new_value) {
                    this.$el.find('div.oe_mail_thread_more:last').show();
            } else {
                    this.$el.find('div.oe_mail_thread_more:last').hide();
            }
        },

        display_user_avatar: function () {
            var avatar = mail.ChatterUtils.get_image(this.session.prefix, this.session.session_id, 'res.users', 'image_small', this.options.uid);
            return this.$el.find('img.oe_mail_icon').attr('src', avatar);
        },
        
        message_post: function (body) {
            var self = this;
            if (! body) {
                var comment_node = this.$el.find('textarea');
                var body = comment_node.val();
                comment_node.val('');
            }
            return this.ds_post.call('message_post', [
                [this.options.context.res_id], body, false, 'comment', this.options.context.parent_id]
                ).then(this.proxy('message_fetch'));
        },

        /** Action: 'shows more' to fetch new messages */
        do_message_fetch: function () {
            return this.message_fetch(this.fetch_more_domain, this.fetch_more_context);
        },

        // TDE: keep currently because need something similar
        // /**
        //  * Create a domain to fetch new comments according to
        //  * comment already present in comments_structure
        //  * @param {Object} comments_structure (see chatter utils)
        //  * @returns {Array} fetch_domain (OpenERP domain style)
        //  */
        // get_fetch_domain: function (comments_structure) {
        //     var domain = [];
        //     var ids = comments_structure.root_ids.slice();
        //     var ids2 = [];
        //     // must be child of current parent
        //     if (this.options.parent_id) { domain.push(['id', 'child_of', this.options.parent_id]); }
        //     _(comments_structure.root_ids).each(function (id) { // each record
        //         ids.push(id);
        //         ids2.push(id);
        //     });
        //     if (this.options.parent_id != false) {
        //         ids2.push(this.options.parent_id);
        //     }
        //     // must not be children of already fetched messages
        //     if (ids.length > 0) {
        //         domain.push('&');
        //         domain.push('!');
        //         domain.push(['id', 'child_of', ids]);
        //     }
        //     if (ids2.length > 0) {
        //         domain.push(['id', 'not in', ids2]);
        //     }
        //     return domain;
        // },
    });


    /** 
     * ------------------------------------------------------------
     * mail_thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of the Chatter on documents.
     */

    /* Add mail_thread widget to registry */
    session.web.form.widgets.add('mail_thread', 'openerp.mail.RecordThread');

    /** mail_thread widget: thread of comments */
    mail.RecordThread = session.web.form.AbstractField.extend({
        // QWeb template to use when rendering the object
        template: 'mail.record_thread',

        init: function() {
            this._super.apply(this, arguments);
            this.options.domain = this.options.domain || [];
            this.options.context = {'res_model': 'mail.thread', 'res_id': false, 'parent_id': false};
            this.options.thread_level = this.options.thread_level || 0;
            this.thread_list = [];
        },

        start: function() {
            // this._super.apply(this, arguments);
            // NB: all the widget should be modified to check the actual_mode property on view, not use
            // any other method to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
        },

        _check_visibility: function() {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },

        destroy: function() {
            for (var i in this.thread_list) { this.thread_list[i].destroy(); }
            this._super.apply(this, arguments);
        },

        set_value: function() {
            var self = this;
            this._super.apply(this, arguments);
            if (! this.view.datarecord.id || session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$el.find('oe_mail_thread').hide();
                return;
            }
            // update context
            this.options.context['res_id'] = this.view.datarecord.id;
            this.options.context['res_model'] = this.view.model;
            // create and render Thread widget
            this.$el.find('div.oe_mail_recthread_main').empty();
            for (var i in this.thread_list) { this.thread_list[i].destroy(); }
            console.log(this);
            var thread = new mail.Thread(self, {
                'context': this.options.context, 'uid': this.session.uid,
                'thread_level': this.options.thread_level, 'show_header_compose': true,
                'show_delete': true, 'composer': true });
            this.thread_list.push(thread);
            return thread.appendTo(this.$el.find('div.oe_mail_recthread_main'));
        },
    });


    /** 
     * ------------------------------------------------------------
     * Wall Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of the Chatter on the Wall.
     */

    /* Add WallView widget to registry */
    session.web.client_actions.add('mail.wall', 'session.mail.Wall');

    /* WallView widget: a wall of messages */
    mail.Wall = session.web.Widget.extend({
        template: 'mail.wall',

        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         * @param {Number} [options.domain] domain on the Wall, is an array.
         * @param {Number} [options.domain] context, is an object. It should
         *      contain res_model, res_id, parent_id, to give it to the threads.
         */
        init: function (parent, options) {
            this._super(parent);
            this.options = options || {};
            this.options.domain = options.domain || [];
            this.options.context = options.context || {};
            this.options.thread_level = options.thread_level || 1;
            this.thread_list = [];
            this.ds_msg = new session.web.DataSet(this, 'mail.message');
            // for search view
            this.search = {'domain': [], 'context': {}, 'groupby': {}}
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}}
        },

        start: function () {
            this._super.apply(this, arguments);
            var search_view_ready = this.load_search_view({}, false);
            var thread_displayed = this.display_thread();
            return (search_view_ready && thread_displayed);
        },

        destroy: function () {
            for (var i in this.thrad_list) { this.thread_list[i].destroy(); }
            this._super.apply(this, arguments);
        },

        /**
         * Override-hack of do_action: automatically reload the chatter.
         * Normally it should be called only when clicking on 'Post/Send'
         * in the composition form. */
        //TDE: still useful ? TO CHECK
        do_action: function(action, on_close) {
            console.log('wall do_action');
            if (this.compose_message_widget) {
                this.compose_message_widget.refresh(); }
            this.message_clean();
            this.display_thread();
            return this._super(action, on_close);
        },

        /**
         * Load the mail.message search view
         * @param {Object} defaults ??
         * @param {Boolean} hidden some kind of trick we do not care here
         */
        load_search_view: function (defaults, hidden) {
            var self = this;
            this.searchview = new session.web.SearchView(this, this.ds_msg, false, defaults || {}, hidden || false);
            return this.searchview.appendTo(this.$el.find('.oe_view_manager_view_search')).then(function () {
                self.searchview.on_search.add(self.do_searchview_search);
            });
        },

        /**
         * Aggregate the domains, contexts and groupbys in parameter
         * with those from search form, and then calls fetch_comments
         * to actually fetch comments
         * @param {Array} domains
         * @param {Array} contexts
         * @param {Array} groupbys
         */
        do_searchview_search: function(domains, contexts, groupbys) {
            var self = this;
            this.rpc('/web/session/eval_domain_and_context', {
                domains: domains || [],
                contexts: contexts || [],
                group_by_seq: groupbys || []
            }, function (results) {
                self.search_results['context'] = results.context;
                self.search_results['domain'] = results.domain;
                self.search_results['groupby'] = results.group_by;
                self.message_clean();
                return self.display_thread();
            });
        },

        /** Clean the wall */
        message_clean: function() {
            this.$el.find('ul.oe_mail_wall_threads').empty();
        },

        /** Display comments
         * @param {Array} records tree structure of records
         */
        display_thread: function () {
            var render_res = session.web.qweb.render('mail.wall_thread_container', {});
            $('<li class="oe_mail_wall_thread">').html(render_res).appendTo(this.$el.find('ul.oe_mail_wall_threads'));
            var thread = new mail.Thread(this, {
                'domain': this.options.domain, 'context': this.options.context, 'uid': this.session.uid,
                'thread_level': this.options.thread_level, 'composer': true,
                // display options
                'show_header_compose': true,  'show_reply': this.options.thread_level > 0,
                'show_hide': true, 'show_reply_by_email': true,
                }
            );
            thread.appendTo(this.$el.find('li.oe_mail_wall_thread:last'));
            this.thread_list.push(thread);
        },
    });
};
