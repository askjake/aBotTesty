import { FC } from 'react';
import Image from 'next/image';
import { StyledWelcomeBlock } from '@shared/ui/components/molecules/Chat/WelcomeBlock/WelcomeBlock.styled';

import { WelcomeBlockProps } from '@shared/ui/components/molecules/Chat/WelcomeBlock/WelcomeBlock.props';

const WelcomeBlock: FC<WelcomeBlockProps> = ({
  className = '',
  logo = '/img/logo.png',
  ...props
}) => {
  return (
    <StyledWelcomeBlock
      className={`welcome-block ${className}`}
      variant='borderless'
      icon={
        <Image src={logo} alt='logo' width={85} quality={100} height={64} />
      }
      title="Hello, I'm Dish Chat"
      description='How can I help you today?'
      {...props}
    />
  );
};

export default WelcomeBlock;
