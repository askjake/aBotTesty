import { useEffect, useRef, useState } from 'react';

import { getHealth } from '@shared/ui/services/health.services';

import {
  StyledHealthBlock,
  StyledHealthBlockIcon,
} from '@shared/ui/components/molecules/Footer/HealthBlock/HealthBlock.styled';

import { HealthStatusEnum } from '@shared/ui/enums/health.enums';

const HealthBlock = () => {
  const [hasError, setHasError] = useState<boolean>(false);
  const [version, setVersion] = useState<string>('1.0.0');
  const interval = useRef<NodeJS.Timeout | null>(null);

  const checkStatus = async () => {
    try {
      const { status, version } = await getHealth();
      setVersion(version);
      setHasError(status === HealthStatusEnum.UNHEALTHY);
    } catch (e) {
      console.error(e);
      setHasError(true);
    }
  };

  useEffect(() => {
    checkStatus();

    interval.current = setInterval(() => {
      checkStatus();
    }, 1000 * 60);
    return () => {
      if (interval.current) {
        clearInterval(interval.current);
      }
    };
  }, []);

  return (
    <StyledHealthBlock className='health-block'>
      <StyledHealthBlockIcon $hasError={hasError} />
      <span>API v{version}</span>
    </StyledHealthBlock>
  );
};

export default HealthBlock;
