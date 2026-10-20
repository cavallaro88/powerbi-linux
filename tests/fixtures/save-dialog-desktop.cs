// SPDX-License-Identifier: GPL-3.0-or-later
// Own synthetic method with the supported call shape; contains no customer data.
using System;
using System.Windows.Forms;
using Microsoft.Mashup.DocumentServices.Strings;
using Microsoft.Mashup.Client.UI.Shared;

namespace Microsoft.Mashup.DocumentServices.Strings
{
    public sealed class LocalizedString
    {
        readonly string text;
        public LocalizedString(string value) { text = value; }
        public static implicit operator string(LocalizedString value) { return value.text; }
    }
}
namespace Microsoft.PowerBI.Client.Windows
{
    public interface IWindowService
    {
        ModalDialogResult ShowYesNoCancelDialog(LocalizedString title, LocalizedString message,
            LocalizedString save, LocalizedString discard, LocalizedString cancel);
    }
    public class MainForm : Form
    {
        public virtual IWindowService WindowService { get { throw new Exception("HTML fixture must not execute"); } }
    }
    public static class PowerBIResources
    {
        public static LocalizedString PowerBIProductName { get { return new LocalizedString("Teste sintético — confirmação de salvamento"); } }
    }
    public static class PowerBIStringResources
    {
        public static LocalizedString SaveChangesPromptMessage { get { return new LocalizedString("Pergunta de teste. Nenhum relatório será salvo ou descartado."); } }
        public static LocalizedString SaveChangesPromptSaveButtonLabel { get { return new LocalizedString("Salvar"); } }
        public static LocalizedString SaveChangesPromptDontSaveButtonLabel { get { return new LocalizedString("Não salvar"); } }
        public static LocalizedString CancelButtonText { get { return new LocalizedString("Cancelar"); } }
    }
    public class ApplicationCloseHandler
    {
        readonly MainForm mainForm;
        public ApplicationCloseHandler(MainForm owner) { mainForm = owner; }
        public ModalDialogResult ShowYesNoCancelSaveChangesPrompt()
        {
            return mainForm.WindowService.ShowYesNoCancelDialog(PowerBIResources.PowerBIProductName,
                PowerBIStringResources.SaveChangesPromptMessage, PowerBIStringResources.SaveChangesPromptSaveButtonLabel,
                PowerBIStringResources.SaveChangesPromptDontSaveButtonLabel, PowerBIStringResources.CancelButtonText);
        }
        // Ensures the fixture includes the same LocalizedString conversion reference.
        public string ConversionReference(LocalizedString value) { return value; }
    }
}
