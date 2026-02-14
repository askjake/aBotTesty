import React from 'react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import VersionsSwitcher from '@shared/ui/components/atoms/VersionsSwitcher';
import { fireEvent, screen } from '@testing-library/react';

describe('VersionsSwitcher Component', () => {
  it('renders without crashing', () => {
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={1}
        updateCurrentVersion={() => {}}
      />,
    );
    expect(screen.getByText('2/3')).toBeInTheDocument();
  });

  it('disables the left button when on the first version', () => {
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={0}
        updateCurrentVersion={() => {}}
      />,
    );
    const leftButton = screen.getByTestId('left-button');
    expect(leftButton).toHaveStyle('filter: brightness(15);');
    expect(leftButton).toHaveStyle('cursor: not-allowed;');
  });

  it('disables the right button when on the last version', () => {
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={2}
        updateCurrentVersion={() => {}}
      />,
    );
    const rightButton = screen.getByTestId('right-button');
    expect(rightButton).toHaveStyle('filter: brightness(15);');
    expect(rightButton).toHaveStyle('cursor: not-allowed;');
  });

  it('calls updateCurrentVersion with the correct index when clicking the left button', () => {
    const updateCurrentVersionMock = jest.fn();
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={1}
        updateCurrentVersion={updateCurrentVersionMock}
      />,
    );
    const leftButton = screen.getByTestId('left-button');
    fireEvent.click(leftButton);
    expect(updateCurrentVersionMock).toHaveBeenCalledWith(0);
  });

  it('calls updateCurrentVersion with the correct index when clicking the right button', () => {
    const updateCurrentVersionMock = jest.fn();
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={1}
        updateCurrentVersion={updateCurrentVersionMock}
      />,
    );
    const rightButton = screen.getByTestId('right-button');
    fireEvent.click(rightButton);
    expect(updateCurrentVersionMock).toHaveBeenCalledWith(2);
  });

  it('does not call updateCurrentVersion when clicking the left button if it is disabled', () => {
    const updateCurrentVersionMock = jest.fn();
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={0}
        updateCurrentVersion={updateCurrentVersionMock}
      />,
    );
    const leftButton = screen.getByTestId('left-button');
    fireEvent.click(leftButton);
    expect(updateCurrentVersionMock).not.toHaveBeenCalled();
  });

  it('does not call updateCurrentVersion when clicking the right button if it is disabled', () => {
    const updateCurrentVersionMock = jest.fn();
    renderLayout(
      <VersionsSwitcher
        totalVersions={3}
        currentIndex={2}
        updateCurrentVersion={updateCurrentVersionMock}
      />,
    );
    const rightButton = screen.getByTestId('right-button');
    fireEvent.click(rightButton);
    expect(updateCurrentVersionMock).not.toHaveBeenCalled();
  });
});
