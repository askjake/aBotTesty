import React from 'react';

export default (importFunc: any, options?: any) => {
  const DynamicComponent = (props: any) => {
    const [Component, setComponent] = React.useState<any>(null);
    const [error, setError] = React.useState<any>(null);

    React.useEffect(() => {
      let isMounted = true;

      const loadComponent = async () => {
        try {
          const importResult = importFunc();

          // Handle both sync and async imports
          const module =
            importResult && typeof importResult.then === 'function'
              ? await importResult
              : importResult;

          if (!isMounted) return;

          // Extract the component
          const ResolvedComponent = module?.default || module;

          if (typeof ResolvedComponent === 'function') {
            setComponent(() => ResolvedComponent);
          } else {
            console.error(
              'Dynamic import did not resolve to a component:',
              module,
            );
            setError(new Error('Invalid component'));
          }
        } catch (err) {
          console.error('Error loading dynamic component:', err);
          if (isMounted) {
            setError(err);
          }
        }
      };

      loadComponent();

      return () => {
        isMounted = false;
      };
    }, []);

    if (error) {
      return null;
    }

    if (!Component) {
      // Return loading state or null
      return options?.loading ? React.createElement(options.loading) : null;
    }

    return React.createElement(Component, props);
  };

  DynamicComponent.displayName = options?.displayName || 'DynamicComponent';
  return DynamicComponent;
};
