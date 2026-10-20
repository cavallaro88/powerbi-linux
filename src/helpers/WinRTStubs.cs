// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using Windows.Foundation;

[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]

namespace Windows.Foundation
{
    public interface IAsyncOperation<T>
    {
    }
}

namespace Windows.Foundation.Metadata
{
    public static class ApiInformation
    {
        public static bool IsTypePresent(string typeName)
        {
            return false;
        }

        public static bool IsMethodPresent(string typeName, string methodName)
        {
            return false;
        }
    }
}

namespace Windows.Storage
{
    public sealed class StorageFile
    {
        public static IAsyncOperation<StorageFile> GetFileFromPathAsync(string path)
        {
            return null;
        }

        public Windows.Storage.FileProperties.StorageItemContentProperties Properties
        {
            get { return null; }
        }
    }
}

namespace Windows.Storage.FileProperties
{
    public sealed class StorageItemContentProperties
    {
        public IAsyncOperation<IDictionary<string, object>> RetrievePropertiesAsync(IEnumerable<string> propertiesToRetrieve)
        {
            return null;
        }
    }
}

namespace Windows.System
{
    public static class Launcher
    {
        public static IAsyncOperation<bool> LaunchUriAsync(Uri uri)
        {
            return null;
        }
    }
}
