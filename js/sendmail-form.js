(function() {
    'use strict';

    const SENDER_SUFFIX = '__WITH_DEFINED_SENDER__';
    const DIRECT_SMTP = '__DKU__DIRECT_SMTP__';

    function getTemplateUpdates(template, config, choices) {
        const updates = {};
        let channel = config.mail_channel;
        if (template.channelId != null) {
            const channelId = template.channelId.trim() ? template.channelId : '';
            const choice = choices.find(item => channelId
                ? item.value === channelId || item.value === channelId + SENDER_SUFFIX
                : item.value == null || item.value === DIRECT_SMTP);
            if (choice) {
                channel = choice.value;
                updates.mail_channel = channel;
            }
        }
        if (template.recipient != null) {
            updates.recipient_column = template.recipient.trim() ? template.recipient : '';
        }
        ['subject', 'sender'].forEach(function(field) {
            if (field === 'sender' && channel && channel.endsWith(SENDER_SUFFIX)) {
                return;
            }
            if (template[field] != null) {
                const target = field + (config['use_' + field + '_value'] ? '_value' : '_column');
                updates[target] = template[field].trim() ? template[field] : '';
            }
        });
        updates.use_body_value = true;
        updates.body_format = template.sendAsHTML ? 'html' : 'text';
        updates[template.sendAsHTML ? 'html_body_value' : 'body_value'] = template.content;
        return updates;
    }

    angular.module('dataiku.sendmail', []).controller('SendmailFormController', ['$scope', '$q', 'EnterpriseAssetLibraryModalService', 'EnterpriseAssetUsageTargetResolver', 'DataikuAPI', function($scope, $q, EnterpriseAssetLibraryModalService, EnterpriseAssetUsageTargetResolver, DataikuAPI) {
        $scope.emailTemplateUiState = { pending: false, error: null };

        $scope.openEmailTemplateLibrary = function() {
            if ($scope.viewMode || $scope.emailTemplateUiState.pending) {
                return;
            }
            $scope.emailTemplateUiState.pending = true;
            $scope.emailTemplateUiState.error = null;

            $q.when().then(function() {
                return EnterpriseAssetLibraryModalService.openEmailTemplatePickerModal(EnterpriseAssetUsageTargetResolver.resolve());
            }).then(function(selection) {
                if ($scope.$$destroyed || $scope.viewMode || !selection || selection.type !== 'template') {
                    return;
                }
                const config = $scope.config;
                const snapshot = angular.copy(config);
                const template = selection.template;

                const channelChoices = template.channelId != null ? DataikuAPI.integrations.listChannelsForIntegrationType('mail').then(function(response) {
                    const choices = response.data.map(channel => ({ value: channel.id + (channel.sender || channel.useCurrentUserAsSender ? SENDER_SUFFIX : '') }));
                    choices.push({ value: choices.length ? DIRECT_SMTP : null });
                    return { choices: choices };
                }) : $q.when();
                return channelChoices.then(function(data) {
                    if ($scope.$$destroyed || $scope.viewMode) {
                        return;
                    }
                    if ($scope.config !== config || !angular.equals(config, snapshot)) {
                        throw new Error('Settings changed while applying the template. Please select the template again.');
                    }
                    if (template.channelId != null && !Array.isArray(data && data.choices)) {
                        throw new Error('Could not load email channels. No settings were changed.');
                    }
                    const updates = getTemplateUpdates(template, snapshot, data && data.choices);
                    angular.extend(config, updates);
                    if (template.channelId != null && !('mail_channel' in updates)) {
                        $scope.emailTemplateUiState.error = 'Template applied, but channel "' + template.channelId + '" is unavailable. The current channel was kept.';
                    }
                });
            }).catch(function(error) {
                if (!$scope.$$destroyed) {
                    $scope.emailTemplateUiState.error = error && error.message || 'Could not apply the email template. No settings were changed.';
                }
            }).finally(function() {
                if (!$scope.$$destroyed) {
                    $scope.emailTemplateUiState.pending = false;
                }
            });
        };
    }]);
})();
