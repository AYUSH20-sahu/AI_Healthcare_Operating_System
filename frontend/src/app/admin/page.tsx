export default function AdminPage() {
    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-8">
            <div className="max-w-2xl text-center">
                <h1 className="text-4xl font-bold text-primary-600 mb-4">Admin Console</h1>
                <p className="text-xl text-gray-600 mb-8">
                    Operations, analytics, and system management
                </p>
                <div className="space-y-4">
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Operations Dashboard</h2>
                        <p className="text-gray-600">Real-time clinic/hospital operations monitoring</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Analytics & Reporting</h2>
                        <p className="text-gray-600">Patient flow, resource utilization, outcome metrics</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">User Management</h2>
                        <p className="text-gray-600">Manage doctors, staff, and patient accounts</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">System Configuration</h2>
                        <p className="text-gray-600">Settings, integrations, compliance controls</p>
                    </div>
                </div>
                <a
                    href="/"
                    className="mt-8 inline-block text-primary-600 hover:text-primary-700 font-medium"
                >
                    ← Back to Home
                </a>
            </div>
        </main>
    )
}